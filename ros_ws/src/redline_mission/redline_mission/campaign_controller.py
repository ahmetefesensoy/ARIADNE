"""Player service -> frozen ROS actions -> persisted science records (D017).

One campaign controller owns MissionState in campaign mode. It must not run
beside orientation/nominal mission_manager. No robot velocity or fake odometry
is published. Rover travel requires the actual Nav2 action result.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import time

import rclpy
from rclpy.action import ActionClient
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor, ExternalShutdownException
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.parameter_client import AsyncParameterClient
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import Point, Point32, PoseStamped
from nav2_msgs.action import NavigateToPose
from rosgraph_msgs.msg import Clock
from std_msgs.msg import String
import yaml

from redline_core.campaign import Campaign
from redline_msgs.action import (ExecuteScout, CollectSample, ContactScience, RemoteLibs,
                                NeutronSurvey, Drill, CacheSample, DeployStation)
from redline_msgs.msg import (Alert, CrewState, DecisionRecord, EvidenceRecord,
                             InstrumentProduct, MissionState, SampleRecord)
from redline_msgs.srv import MissionCommand

MAP_QOS = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                     durability=DurabilityPolicy.TRANSIENT_LOCAL)


def _reject_nonfinite(value):
    raise ValueError("nonfinite JSON value: " + value)


class CampaignController(Node):
    def __init__(self, **kwargs):
        super().__init__("campaign_controller", **kwargs)
        get = lambda name, default: self.declare_parameter(name, default).value
        self.run_id = str(get("run_id", datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-BXW_CAMPAIGN-15"))
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", self.run_id):
            raise ValueError("invalid run_id")
        root = Path(str(get("redline_root", ""))).resolve()
        self.output = Path(str(get("campaign_output_dir", str(root / "data/products")))) / self.run_id
        self.output.mkdir(parents=True, exist_ok=True)
        targets = yaml.safe_load(Path(str(get("targets_file", str(root / "config/targets_BXW.yaml")))).read_text())
        self.targets = {t["id"]: tuple(float(v) for v in t["point_m"]) for t in targets["targets"]}
        self.routes = {t["id"]: t.get("route_xy_m",[]) for t in targets["targets"]}
        self.campaign = Campaign({name:point[:2] for name,point in self.targets.items()})
        self.crew = None
        self.crew_receipt = -math.inf
        self._human_position = None
        self._human_pose_receipt = -math.inf
        self.pet_s = 0.
        self.physics_stamp = None
        self.physics_receipt = -math.inf
        self.sep_alert = False
        self.products = {}
        self.samples = {}
        self.evidence = set()
        self._evidence_by_product = {}
        self._evidence_products = {}
        # Bounded presentation history for tablets joining after scout flight.
        # Evidence/action completion gates remain independent of this view.
        self._scout_observations = {}
        self.product_history = []
        self._goal = None
        self._pending_result = None
        self._last_feedback = -math.inf
        self._robot_available = False
        self._active_since = None
        self._cancel_requested = False
        self._continuation = None
        self._state_pub = self.create_publisher(String, "/redline/campaign/state", MAP_QOS)
        self._mission_pub = self.create_publisher(MissionState, "/redline/mission/state", MAP_QOS)
        self._decision_pub = self.create_publisher(DecisionRecord, "/redline/decisions", 50)
        # Coordinator state is serialized; action execution stays asynchronous.
        group = self.default_callback_group
        self.create_service(MissionCommand, "/redline/campaign/command", self._command, callback_group=group)
        self.create_subscription(CrewState, "/crew/EV1/state", self._crew, 10)
        self.create_subscription(PoseStamped,"/crew/EV1/pose",self._human_pose,10)
        self.create_subscription(Clock, "/redline/mission/clock", self._on_mission_clock, 10)
        self.create_subscription(Clock, "/clock", self._on_physics_clock, 10)
        self.create_subscription(InstrumentProduct, "/redline/science/products", self._product, 50)
        self.create_subscription(SampleRecord, "/redline/science/samples", self._sample, 50)
        self.create_subscription(EvidenceRecord, "/redline/evidence", self._evidence_record, 50)
        self.create_subscription(String, "/redline/science/status", self._science_status, 10)
        self.create_subscription(PoseStamped, "/redline/science/rover_pose", self._robot_pose, 10)
        self.create_subscription(Alert, "/redline/alerts", self._alert, 50)
        self._robot_receipt = -math.inf
        self.scout_status = {}
        self._scout_receipt = -math.inf
        self.create_subscription(String,"/scout_1/flight_state",self._scout_status,10)
        endpoints = {"scout": (ExecuteScout, "/scout_1/execute_scout"),
                     "collect": (CollectSample, "/redline/science/collect_sample"),
                     "xrf": (ContactScience, "/rover_1/contact_science"),
                     "libs": (RemoteLibs, "/rover_1/remote_libs"),
                     "dan": (NeutronSurvey, "/rover_1/neutron_survey"),
                     "drill": (Drill, "/rover_1/drill"),
                     "cache": (CacheSample, "/redline/science/cache_sample"),
                     "weather": (DeployStation, "/redline/science/deploy_station")}
        self._action_clients = {k: ActionClient(self, a, name, callback_group=group) for k, (a, name) in endpoints.items()}
        self._nav = ActionClient(self, NavigateToPose, "/rover_1/navigate_to_pose", callback_group=group)
        self._clock_control = AsyncParameterClient(self, "sim_clock", callback_group=group)
        self.create_timer(.25, self._tick)
        self._publish()

    def _crew(self, msg):
        p = msg.pose.pose.position
        if msg.crew_id == "EV1" and msg.header.frame_id == "map" and all(math.isfinite(v) for v in (p.x, p.y, p.z)):
            self.crew, self.crew_receipt = msg, time.monotonic()

    def _on_mission_clock(self, msg):
        self.pet_s = msg.clock.sec + 1e-9 * msg.clock.nanosec

    def _human_pose(self,msg):
        p=msg.pose.position
        if msg.header.frame_id=="map" and all(math.isfinite(v) for v in (p.x,p.y,p.z)):
            self._human_position=(p.x,p.y)
            self._human_pose_receipt=time.monotonic()

    def _on_physics_clock(self, msg):
        self.physics_stamp, self.physics_receipt = msg.clock, time.monotonic()

    def _robot_pose(self, msg):
        p = msg.pose.position
        if msg.header.frame_id == "map" and all(math.isfinite(v) for v in (p.x, p.y, p.z)):
            self._robot_receipt = time.monotonic()

    def _scout_status(self,msg):
        if len(msg.data)>8000:return
        try:
            data=json.loads(msg.data,parse_constant=_reject_nonfinite)
            if not isinstance(data,dict) or data.get("schema")!="redline.scout.flight.v1":return
            self.scout_status,self._scout_receipt=data,time.monotonic()
            if self.campaign.task.kind=="scout" and data.get("request_id")==self.campaign.operation_id:
                self.campaign.feedback(data.get("phase",""),float(data.get("progress",0)))
        except (ValueError,TypeError):return

    def _evidence_record(self, msg):
        if not msg.evidence_id or len(msg.evidence_id) > 256 or len(self.evidence) >= 4096:
            return
        product_id = msg.provenance.product_id
        if msg.evidence_id in self._evidence_products and self._evidence_products[msg.evidence_id] != product_id:
            return
        first_receipt = msg.evidence_id not in self.evidence
        self.evidence.add(msg.evidence_id)
        self._evidence_products[msg.evidence_id] = product_id
        if product_id:
            self._evidence_by_product.setdefault(product_id, set()).add(msg.evidence_id)
        if first_receipt:
            self._retain_scout_observation(msg)

    def _retain_scout_observation(self, msg):
        """Keep received scout points, not hidden-world objects or new detections."""
        p = msg.pose.pose.position
        if (not msg.source.startswith("scout") or len(msg.source.encode("utf-8")) > 64
                or len(msg.evidence_id.encode("utf-8")) > 256
                or msg.header.frame_id != "map"
                or not all(math.isfinite(v) and abs(v) <= 1e7 for v in (p.x, p.y, p.z))
                or not 0 <= int(msg.provenance.status) <= 3
                or len(msg.summary_json.encode("utf-8")) > 8192):
            return
        try:
            summary = json.loads(msg.summary_json, parse_constant=_reject_nonfinite)
        except (ValueError, TypeError, RecursionError):
            return
        if not isinstance(summary, dict):
            return
        passability = summary.get("passability", -1)
        if type(passability) is not int or passability not in (-1, 0, 1):
            passability = -1
        observation = summary.get("cell_observation")
        if (isinstance(observation, dict)
                and observation.get("schema") == "redline.cell_observation.v2"
                and observation.get("state") == "DETECTED"):
            # Both scout publishers omit `passable` for passable detections.
            value = observation.get("passable", True)
            passability = int(value) if type(value) is bool else -1
        if len(self._scout_observations) >= 128:
            self._scout_observations.pop(next(iter(self._scout_observations)))
        self._scout_observations[msg.evidence_id] = {
            "header": {"frame_id": "map"}, "evidence_id": msg.evidence_id,
            "source": msg.source, "pose": {"pose": {"position": {"x": p.x, "y": p.y, "z": p.z}}},
            "provenance": {"status": int(msg.provenance.status)},
            "summary_json": json.dumps({"passability": passability}, separators=(",", ":"))}

    def _alert(self, msg):
        if str(msg.code).startswith("SEP") and int(msg.severity) >= 2:
            self.sep_alert = True
            if self._goal:
                self._goal.cancel_goal_async()
            self.campaign.message = "SEP alarmı: etkin bilim durduruluyor. Habitat dönüşü öncelikli."
            self._publish()

    def _product(self, msg):
        if len(msg.summary_json) > 128000 or len(self.products) >= 512:
            return
        try:
            summary = json.loads(msg.summary_json, parse_constant=_reject_nonfinite)
        except (ValueError, TypeError):
            return
        if not isinstance(summary, dict):
            return
        if msg.product_id in self.products:
            return
        entry = {"product_id": msg.product_id, "instrument": msg.instrument, "target_id": msg.target_id,
                 "status": int(msg.provenance.status), "payload_uri": msg.payload_uri,
                 "integration_s": msg.integration_s, "summary": summary,
                 "target_point_m": [msg.target_point.x, msg.target_point.y, msg.target_point.z]}
        self.products[msg.product_id] = entry
        self.product_history.append(entry)
        self._publish()

    def _sample(self, msg):
        if (not msg.sample_id or len(msg.sample_id) > 256 or not 0 <= msg.state <= SampleRecord.FAILED
                or not all(math.isfinite(v) for v in (msg.origin_point.x, msg.origin_point.y, msg.origin_point.z,
                                                    msg.analysis_point.x, msg.analysis_point.y, msg.analysis_point.z))):
            return
        if len(self.samples) >= 100 and msg.sample_id not in self.samples:
            return
        self.samples[msg.sample_id] = {"sample_id": msg.sample_id, "target_id": msg.target_id,
            "state": int(msg.state), "container_id": msg.container_id, "tool": msg.tool,
            "origin_point_m": [msg.origin_point.x, msg.origin_point.y, msg.origin_point.z],
            "analysis_point_m": [msg.analysis_point.x, msg.analysis_point.y, msg.analysis_point.z],
            "evidence_ids": list(msg.evidence_ids)}

    def _science_status(self, msg):
        if len(msg.data) > 16000:
            return
        try:
            status = json.loads(msg.data, parse_constant=_reject_nonfinite)
            if not isinstance(status, dict):
                return
            if status.get("request_id") == self.campaign.operation_id:
                self.campaign.feedback(status.get("phase", ""), float(status.get("progress", 0)))
        except (ValueError, TypeError):
            return

    def _decision(self, context, chosen, reasons=()):
        record = DecisionRecord()
        record.header.frame_id, record.header.stamp = "map", self.get_clock().now().to_msg()
        record.decision_id = f"dec-{self.run_id}-{self.campaign.revision}"
        record.context, record.chosen = context, chosen
        record.evidence_ids = self.campaign.evidence_ids[-100:]
        record.candidates = [self.campaign.task.id]
        record.rejected_reasons = list(reasons)
        record.model_version = "redline.campaign.v1"
        record.assumptions_json = json.dumps({"status": "SCENARIO", "pet_s": self.pet_s,
                                             "operation_id": self.campaign.operation_id})
        self._decision_pub.publish(record)
        with (self.output / "campaign_decisions.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"utc": datetime.now(timezone.utc).isoformat(), "decision_id": record.decision_id,
                "context": context, "chosen": chosen, "evidence_ids": record.evidence_ids,
                "rejected_reasons": list(reasons), "assumptions": json.loads(record.assumptions_json)}, ensure_ascii=False) + "\n")

    def _command(self, req, response):
        c = self.campaign
        response.revision, response.operation_id = c.revision, c.operation_id
        try:
            if self.sep_alert:
                raise ValueError("SEP etkin: bilim komutları kapalı; habitat dönüşü gerekli")
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}", req.request_id):
                raise ValueError("Komut kimliği güvenli ve en çok 96 karakter olmalı")
            position = self._human_position
            fresh = c.validate_command(req.request_id, req.command, req.target_id, req.expected_revision,
                                       position, time.monotonic() - self._human_pose_receipt)
            if not fresh:
                response.accepted, response.reason = True, "Önceki komut kaydı; tekrar yürütülmedi."
                return response
            if req.command == "CANCEL":
                if self._goal is None:
                    raise ValueError("aksiyon kabulü bekleniyor; az sonra iptal et")
                self._cancel_requested = True
                c.requests[req.request_id] = (req.command, req.target_id, req.expected_revision)
                self._goal.cancel_goal_async()
                response.accepted, response.reason = True, "İptal istendi; ROS sonucunu bekle."
                return response
            kind = c.task.kind
            if self._goal is not None:
                raise ValueError("Önceki aksiyonun durma/iptal sonucunu bekle")
            if kind == "decision" and not self._clock_control.services_are_ready():
                raise ValueError("Görev saati denetimi bağlı değil; saha çıkışı başlatılmadı")
            if kind not in ("briefing", "decision", "assessment", "debrief"):
                if not self._action_clients[kind].server_is_ready():
                    raise ValueError("Gerekli işlem sunucusu bağlı değil: " + kind)
                if kind in ("libs", "dan", "drill") and time.monotonic() - self._robot_receipt > 2:
                    raise ValueError("Roverın güncel ROS/Gazebo konumu yok; işlem başlatılmadı.")
                if kind == "libs" and not self._nav.server_is_ready():
                    raise ValueError("Gazebo/Nav2 navigasyon sunucusu bağlı değil.")
                if kind == "libs" and time.monotonic() - self.physics_receipt > 2:
                    raise ValueError("Gazebo fizik saati güncel değil; navigasyon komutu gönderilmedi.")
            if kind == "cache" and not c.sample_ids:
                raise ValueError("Teslim edilecek alınmış numune yok")
            c.accept(req.request_id, req.command, req.target_id, req.expected_revision)
            self._active_since, self._cancel_requested = time.monotonic(), False
            self._decision("player_command_accepted", req.command)
            if kind == "decision":
                c.feedback("WAITING_FOR_PET_CLOCK", 0.)
                operation_id = c.operation_id
                self._clock_control.set_parameters([Parameter("running", value=True)]).add_done_callback(
                    lambda future: self._egress_started(future, operation_id, req.command))
            elif kind == "assessment":
                c.decide(req.command)
            elif kind in ("briefing", "debrief"):
                c.finish(success=True)
            elif kind == "libs":
                self._dispatch_rover_travel()
            else:
                self._dispatch_science(kind)
            # PET stays paused through the precursor/route review, then starts
            # once on egress. Never change Gazebo /clock or pause resources.
            response.accepted, response.reason = True, "Komut kabul edildi; işlem sonucu ayrıca yayımlanır."
        except (ValueError, KeyError) as error:
            response.accepted, response.reason = False, str(error)
            c.message = str(error)
        response.revision, response.operation_id = c.revision, c.operation_id
        self._publish()
        return response

    def _egress_started(self, future, operation_id, command):
        if operation_id != self.campaign.operation_id or self.campaign.state not in ("pending", "running"):
            return
        try:
            result = future.result()
            if self.sep_alert or result is None or not result.results or not all(r.successful for r in result.results):
                raise ValueError("Görev saati başlatılamadı; saha kararı açık kaldı")
            self.campaign.decide(command)
            self._decision("egress_clock_started", command)
        except Exception as error:
            self._fail(str(error))

    def _dispatch_rover_travel(self):
        p = self.targets[self.campaign.task.target_id]
        goal = NavigateToPose.Goal()
        goal.pose.header.frame_id, goal.pose.header.stamp = "map", self.physics_stamp
        goal.pose.pose.position.x, goal.pose.pose.position.y, goal.pose.pose.position.z = p[0] - 3., p[1], p[2]
        goal.pose.pose.orientation.w = 1.
        self.campaign.feedback("ROVER_NAVIGATING", 0.)
        operation_id = self.campaign.operation_id
        self._nav.send_goal_async(goal, feedback_callback=lambda feedback: self._nav_feedback(feedback, operation_id)).add_done_callback(
            lambda future: self._goal_response(future, "navigate", operation_id))

    def _nav_feedback(self, feedback, operation_id):
        if operation_id == self.campaign.operation_id and self.campaign.state in ("pending", "running"):
            self.campaign.operation_phase = f"ROVER_NAVIGATING · {feedback.feedback.distance_remaining:.1f} m"

    def _dispatch_science(self, kind):
        c = self.campaign
        p = self.targets.get(c.task.target_id, (0., 0., 0.))
        point = Point(x=p[0], y=p[1], z=p[2])
        if kind == "scout":
            goal = ExecuteScout.Goal(request_id=c.operation_id, vehicle_id="scout_1", altitude_m=20., max_flight_s=600.)
            # Explicit authored SCENARIO region, away from the crew; only the
            # scout node sees the hidden world, never this controller.
            goal.corridor.points = [Point32(x=float(x), y=float(y)) for x, y in
                                     ((330, -474), (354, -474), (354, -450), (330, -450))]
        elif kind == "collect":
            goal = CollectSample.Goal(request_id=c.operation_id, crew_id="EV1", target_id=c.task.target_id,
                target_point=point, container_id=f"container-{self.run_id}-01")
        elif kind == "xrf":
            goal = ContactScience.Goal(request_id=c.operation_id, target_id=c.task.target_id, target_point=point,
                                       instrument="EV1_XRF", integration_s=20.)
        elif kind == "weather":
            goal = DeployStation.Goal(request_id=c.operation_id, deployer_id="EV1", station_type=1, position=point)
        elif kind == "libs":
            goal = RemoteLibs.Goal(request_id=c.operation_id, target_id=c.task.target_id, raster_rows=2,
                                  raster_cols=2, raster_spacing_mrad=2., shots_per_point=10)
        elif kind == "dan":
            goal = NeutronSurvey.Goal(request_id=c.operation_id, vehicle_id="rover_1", mode=1, max_points=1, dwell_s=20.)
            goal.area.points = [Point32(x=float(p[0]+x), y=float(p[1]+y)) for x,y in ((-6,-4),(4,-4),(4,4),(-6,4))]
        elif kind == "drill":
            goal = Drill.Goal(request_id=c.operation_id, target_id=c.task.target_id, depth_mm=50., mode=0)
        elif kind == "cache":
            # CollectSample sample, not a different drill sample, goes to lab.
            goal = CacheSample.Goal(request_id=c.operation_id, sample_id=c.sample_ids[0],
                                     container_id=f"container-{self.run_id}-01")
        else:
            raise ValueError("unsupported operation")
        operation_id = c.operation_id
        self._action_clients[kind].send_goal_async(goal, feedback_callback=lambda f: self._feedback(kind, f, operation_id)).add_done_callback(
            lambda future: self._goal_response(future, kind, operation_id))

    def _feedback(self, kind, wrapped, operation_id):
        if operation_id != self.campaign.operation_id or self.campaign.state not in ("pending", "running"):
            return
        feedback = wrapped.feedback
        phase = getattr(feedback, "phase", kind.upper())
        progress = float(getattr(feedback, "progress", getattr(feedback, "covered_fraction", 0.)))
        if kind == "libs": progress = min(float(feedback.points_done) / 4., 1.)
        self.campaign.feedback(phase, progress)

    def _goal_response(self, future, kind, operation_id):
        try:
            handle = future.result()
            if operation_id != self.campaign.operation_id:
                if handle is not None and handle.accepted:
                    handle.cancel_goal_async()
                return
            if handle is None or not handle.accepted:
                raise ValueError("İşlem ROS tarafından reddedildi: " + kind)
            self._goal = handle
            handle.get_result_async().add_done_callback(lambda result: self._result(result, kind, operation_id))
            if self._cancel_requested or self.sep_alert or self.campaign.state not in ("pending", "running"):
                handle.cancel_goal_async()
        except Exception as error:
            if operation_id == self.campaign.operation_id:
                self._fail(str(error))

    def _result(self, future, kind, operation_id):
        if operation_id != self.campaign.operation_id:
            return
        self._goal = None
        if self.campaign.state not in ("pending", "running"):
            return
        try:
            wrapped = future.result()
            if self._cancel_requested or self.sep_alert:
                raise ValueError("İşlem iptal edildi; görev tamamlanmış sayılmadı")
            if wrapped.status != GoalStatus.STATUS_SUCCEEDED:
                raise ValueError(f"İşlem tamamlanmadı (ROS {wrapped.status}): {getattr(wrapped.result, 'reason', '')}")
            if kind == "navigate":
                if wrapped.result.error_code != 0:
                    raise ValueError("Nav2 hedefe varamadı")
                if self._cancel_requested or self.sep_alert:
                    raise ValueError("Varış sonrası işlem iptal edildi")
                self._dispatch_science("libs")
                return
            result = wrapped.result
            if result.outcome != 0:
                raise ValueError("İşlem sonucu başarılı değil: " + result.reason)
            self._pending_result = (kind, result, time.monotonic())
        except Exception as error:
            self._fail(str(error))

    def _fail(self, reason):
        self._pending_result = None
        if self.campaign.state in ("pending", "running"):
            self.campaign.finish(success=False, reason=reason)
            self._decision("operation_failed", self.campaign.task.id, [reason])
        self._publish()

    def _tick(self):
        if self._pending_result:
            kind, result, since = self._pending_result
            products = list(getattr(result, "product_ids", []))
            if getattr(result, "product_id", ""): products.append(result.product_id)
            # Frozen CacheSample / DeployStation omit product IDs; join the
            # current operation through the persisted summary request_id.
            if kind in ("cache", "weather", "drill"):
                products = [pid for pid, item in self.products.items()
                            if item["summary"].get("request_id") == self.campaign.operation_id]
            evidence = list(getattr(result, "evidence_ids", []))
            for product_id in products:
                evidence.extend(self._evidence_by_product.get(product_id, ()))
            evidence = sorted(set(evidence))
            samples = [result.sample_id] if getattr(result, "sample_id", "") else []
            if kind == "cache": samples = self.campaign.sample_ids[:1]
            sample_ready = all(s in self.samples and self.samples[s]["state"] >= (7 if kind == "cache" else 5) for s in samples)
            product_lineage_ready = all(p in self.products
                and self.products[p]["summary"].get("request_id") == self.campaign.operation_id
                and bool(self._evidence_by_product.get(p)) for p in products)
            ready = (product_lineage_ready and all(e in self.evidence for e in evidence)
                     and sample_ready and (bool(products) or kind == "scout"))
            if ready:
                try:
                    old = self.campaign.task.id
                    self.campaign.finish(success=True, products=products, evidence=evidence, samples=samples)
                    self._decision("operation_result_recorded", old)
                    self._pending_result = None
                except ValueError as error:
                    self._fail(str(error))
            elif time.monotonic() - since > 6:
                self._fail("Sonuç geldi fakat ürün/kanıt/numune kaydı doğrulanamadı; görev açık.")
        if self._active_since and time.monotonic() - self._active_since > 900 and self.campaign.state in ("pending", "running"):
            if self._goal: self._goal.cancel_goal_async()
            self._fail("İşlem zaman aşımı; roverı denetle.")
        self._publish()

    def _publish(self):
        snapshot = self.campaign.snapshot(self._human_position, time.monotonic() - self._human_pose_receipt)
        # Arrival is presentation only: it never advances a task. SEP remains
        # a controller command gate even for remotely requested robot work.
        if self.sep_alert:
            for task in snapshot["tasks"]:
                if task["presentation"]["state"] == "active":
                    task["presentation"].update(enabled=False, blocked_reason="sep_alert")
        target_id=self.campaign.task.target_id
        if target_id not in self.routes:target_id="BXW_RIDGE_A" if self.campaign.branch=="ridge" else "BXW_HOLLOW_B"
        route=self.routes.get(target_id,[])
        snapshot["route_xy_m"] = list(reversed(route)) if self.campaign.task.kind in ("cache","assessment","debrief") else route
        snapshot.update(run_id=self.run_id, pet_s=self.pet_s, products=self.product_history[-20:],
            samples=list(self.samples.values())[-20:], sep_alert=self.sep_alert,
            rover_connected=time.monotonic() - self._robot_receipt <= 2,
            scout=self.scout_status,scout_age_s=min(9999.,time.monotonic()-self._scout_receipt),
            scout_observations=list(self._scout_observations.values()),
            robot_physics="ROS/Gazebo", science_backend="SIMULATED / UNCALIBRATED_SCENARIO")
        text = json.dumps(snapshot, ensure_ascii=False, allow_nan=False)
        # This optional view must not crowd out the existing mission contract.
        # Retain all 128 in memory but send the newest points that fit its cap.
        while len(text.encode("utf-8")) > 240000 and snapshot["scout_observations"]:
            snapshot["scout_observations"].pop(0)
            text = json.dumps(snapshot, ensure_ascii=False, allow_nan=False)
        if len(text.encode("utf-8")) > 240000:
            self.get_logger().error("campaign snapshot exceeds bounded transport")
            return
        self._state_pub.publish(String(data=text))
        state = MissionState()
        state.header.frame_id, state.header.stamp = "map", self.get_clock().now().to_msg()
        state.run_id, state.scenario_id = self.run_id, "BXW_CAMPAIGN"
        state.phase = 5 if self.sep_alert else 6 if self.campaign.done else self.campaign.task.phase
        state.active_task_ids = [] if self.campaign.done else [self.campaign.task.id]
        state.active_plan_id = "campaign-" + self.campaign.branch
        state.pet_min = self.pet_s / 60.
        self._mission_pub.publish(state)
        (self.output / "campaign_state.json").write_text(text + "\n", encoding="utf-8")


def main(args=None):
    rclpy.init(args=args)
    node = CampaignController()
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)
    try:
        executor.spin()
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        executor.shutdown()
        node.destroy_node()
        rclpy.try_shutdown()

