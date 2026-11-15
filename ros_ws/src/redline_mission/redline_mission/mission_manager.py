"""Mission state machine (proje.md §8.3 `mission_manager`, §8.7; D012, D015).

``nominal_flow`` (D015): BRIEFING asks planner_server for plan v1 (PlanEva), then
(PRECURSOR →) TRAVERSE ⇄ STATION_SCIENCE → RETURN → DEBRIEF from redline_core.mission_flow on the
plan schedule and the crew positions. Mission time is held until TRAVERSE; the walk schedule
starts at ``egress_pet_s`` (the same value ev_sim uses), and the scenario player starts the
clock (ScenarioControl START). The orientation walkthrough (``intro_enabled``) is a separate run.

``precursor`` (T7, D015): in PRECURSOR the best robot task proposal of voi_tasker is flown by
``scout_1`` (ExecuteScout over the proposal's survey area, a ``robot_task_dispatch`` record). When
all scout evidence is in the latched known cells, blocked cells within ``route_clearance_m``
of the planned route trigger a replan; plan v2 is accepted only when planner_server's decision
names the blocking evidence (evidence gate, bounded retries). Otherwise the record says the route
was clear and plan v1 is kept. Replanning happens only before egress: PlanEva has no start state.

Phases follow MissionState. This T6 subset handles the SEP path of §8.7:
TRAVERSE/STATION_SCIENCE → CONTINGENCY on the rising edge of ``/env/dose_rate`` alert,
→ RETURN once the ReturnToShelter goal is accepted, → DEBRIEF when it succeeds. Every
transition writes a DecisionRecord; the alarm raises an EMERGENCY Alert. "Shelter mode"
for FR-04 is phase ∈ {CONTINGENCY, RETURN, DEBRIEF}. The state is published on every
change and at 2 Hz with the mission PET.
"""
from __future__ import annotations

import json
import math
import time

import rclpy
from geometry_msgs.msg import Point32
from action_msgs.msg import GoalStatus
from rclpy.action import ActionClient
from rclpy.qos import QoSProfile as _QoS
from rclpy.clock import Clock as RclClock
from rclpy.clock import ClockType
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.parameter_client import AsyncParameterClient
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from rosgraph_msgs.msg import Clock

from redline_msgs.action import ExecuteScout, ReturnToShelter
from redline_msgs.msg import Alert, CellDelta, CrewState, DecisionRecord, DoseRate, EVAPlan, MissionState
from redline_msgs.srv import PlanEva, ScenarioControl
from std_srvs.srv import Trigger
from redline_core.eva_intro import IntroLocations, advance_intro
from redline_core.mission_flow import NominalFlow
from redline_core.plan_follow import PlanSchedule

STATE_TOPIC = "/redline/mission/state"
ALERT_TOPIC = "/redline/alerts"
DECISION_TOPIC = "/redline/decisions"
RTS_ACTION = "/redline/return_to_shelter"
SHELTER_PHASES = (MissionState.CONTINGENCY, MissionState.RETURN, MissionState.DEBRIEF)
PHASES = {"BRIEFING": 0, "PRECURSOR": 1, "TRAVERSE": 2, "STATION_SCIENCE": 3, "RETURN": 4, "CONTINGENCY": 5,
          "DEBRIEF": 6}
MAP_QOS = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=1, reliability=ReliabilityPolicy.RELIABLE,
                     durability=DurabilityPolicy.TRANSIENT_LOCAL)
STATE_QOS = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=10, reliability=ReliabilityPolicy.RELIABLE,
                       durability=DurabilityPolicy.VOLATILE)
EVENT_QOS = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=50, reliability=ReliabilityPolicy.RELIABLE,
                       durability=DurabilityPolicy.VOLATILE)
SCOUT_OUTCOMES = {ExecuteScout.Result.SUCCEEDED: "SUCCEEDED", ExecuteScout.Result.PARTIAL: "PARTIAL",
                  ExecuteScout.Result.CANCELED: "CANCELED", ExecuteScout.Result.FAILED: "FAILED",
                  ExecuteScout.Result.REJECTED: "REJECTED"}
GOAL_STATUSES = {GoalStatus.STATUS_SUCCEEDED: "SUCCEEDED", GoalStatus.STATUS_CANCELED: "CANCELED",
                 GoalStatus.STATUS_ABORTED: "ABORTED", GoalStatus.STATUS_UNKNOWN: "UNKNOWN"}


def schedule_from_plan(plan: EVAPlan, start_pet_s: float) -> PlanSchedule:
    route = [(p.pose.position.x, p.pose.position.y) for p in plan.route.poses]
    stations = [((s.position.x, s.position.y), 60.0 * s.service_min) for s in plan.stations]
    return PlanSchedule.from_plan(route, stations, [60.0 * leg.duration_min for leg in plan.legs], start_pet_s)


class MissionManagerNode(Node):
    def __init__(self, **kwargs):
        super().__init__("mission_manager", **kwargs)
        self.crew_ids = list(self.declare_parameter("crew_ids", ["EV1"]).value)
        self.run_id = str(self.declare_parameter("run_id", "").value)
        self.scenario_id = str(self.declare_parameter("scenario_id", "").value)
        initial = str(self.declare_parameter("initial_phase", "TRAVERSE").value)
        if initial not in PHASES:
            raise ValueError(f"initial_phase must be one of {sorted(PHASES)}")
        self.phase = PHASES[initial]
        self.intro_enabled = bool(self.declare_parameter("intro_enabled", False).value)
        self.intro_locations = IntroLocations(
            tuple(self.declare_parameter("intro_briefing_xy", [290.0, -454.0]).value),
            tuple(self.declare_parameter("intro_station_xy", [306.0, -454.0]).value))
        self.nominal = bool(self.declare_parameter("nominal_flow", False).value)
        if self.nominal and self.intro_enabled:
            raise ValueError("nominal_flow and the orientation walkthrough (intro_enabled) are separate runs")
        self.site_id = str(self.declare_parameter("site_id", "").value)
        self.egress_pet_s = float(self.declare_parameter("egress_pet_s", 0.0).value)
        self.plan_objective = str(self.declare_parameter("plan_objective", "SCIENCE").value)
        self.plan_max_min = float(self.declare_parameter("plan_max_duration_min", 300.0).value)
        self.plan_targets = [t for t in self.declare_parameter("plan_target_ids", [""]).value if t]
        self.active_plan_id = ""
        self.plan = None
        self._plan_pending = False
        self._clock_started = False
        self._crew_xy: dict[str, tuple[float, float]] = {}
        self.precursor = bool(self.declare_parameter("precursor", False).value)
        self.precursor_vehicle = str(self.declare_parameter("precursor_vehicle", "scout_1").value)
        self.route_clearance_m = float(self.declare_parameter("route_clearance_m", 4.0).value)
        self.evidence_retries = int(self.declare_parameter("evidence_retries", 5).value)
        self._pre_state = "wait"
        self._proposal = None
        self._scout_result = None
        self._scout_status = GoalStatus.STATUS_UNKNOWN
        self._scout_since = math.nan
        self._known_blocked: dict[tuple[int, int], str] = {}
        self._known_evidence: set[str] = set()
        self._geometry = None
        self._planner_evidence: dict[str, list[str]] = {}
        self._replan = None
        self._replan_attempts = 0
        self._decision_counter = 0
        self._ev1_xy, self._ev1_receipt = None, -math.inf
        self._clock_pending = False
        self.pet_s = math.nan
        self.sep_alert = False
        self.transitions: list[tuple[float, int, int]] = []
        self.task_ids: list[str] = []
        self.counter = 0
        self._state_pub = self.create_publisher(MissionState, STATE_TOPIC, MAP_QOS)
        self._alert_pub = self.create_publisher(Alert, ALERT_TOPIC, EVENT_QOS)
        self._decision_pub = self.create_publisher(DecisionRecord, DECISION_TOPIC, EVENT_QOS)
        self.create_subscription(Clock, "/redline/mission/clock", self._on_clock, STATE_QOS)
        self.create_subscription(DoseRate, "/env/dose_rate", self._on_dose, STATE_QOS)
        # S2 (§8.7): rule_monitor detects a suit leak from telemetry; the response is a return home.
        self.create_subscription(Alert, ALERT_TOPIC, self._on_alert, EVENT_QOS)
        self._rts = ActionClient(self, ReturnToShelter, RTS_ACTION)
        if self.intro_enabled:
            self.create_subscription(CrewState, "/crew/EV1/state", self._on_ev1, STATE_QOS)
            self.create_service(Trigger, "/redline/mission/advance", self._on_advance)
            self._clock_control = AsyncParameterClient(self, "/sim_clock")
        steady = RclClock(clock_type=ClockType.STEADY_TIME)
        if self.nominal:
            self.flow = NominalFlow(self.crew_ids, shelter_xy=(math.nan, math.nan), precursor=self.precursor)
            if self.precursor:
                latched = _QoS(history=HistoryPolicy.KEEP_LAST, depth=1, reliability=ReliabilityPolicy.RELIABLE,
                               durability=DurabilityPolicy.TRANSIENT_LOCAL)
                self.create_subscription(DecisionRecord, "/redline/robot_tasks/proposed",
                                         lambda m: setattr(self, "_proposal", m), latched)
                self.create_subscription(CellDelta, "/redline/cells/known", self._on_known, latched)
                # Snapshot cells retain only their newest evidence id. The
                # per-observation delta confirms earlier overlapping records.
                self.create_subscription(CellDelta, "/redline/cells/delta", self._on_known, EVENT_QOS)
                self.create_subscription(DecisionRecord, DECISION_TOPIC, self._on_decision, EVENT_QOS)
                self._scout = ActionClient(self, ExecuteScout, f"/{self.precursor_vehicle}/execute_scout")
            for crew_id in self.crew_ids:
                self.create_subscription(CrewState, f"/crew/{crew_id}/state",
                                         lambda m, c=crew_id: self._on_crew(c, m), STATE_QOS)
            self._plan_client = self.create_client(PlanEva, "/redline/plan_eva")
            self._scenario_client = self.create_client(ScenarioControl, "/redline/scenario/control")
            self.create_timer(0.25, self._flow_tick, clock=steady)
        self.create_timer(0.5, self._publish_state, clock=steady)

    # --- inputs -----------------------------------------------------------------------
    def _on_clock(self, message: Clock) -> None:
        self.pet_s = message.clock.sec + message.clock.nanosec * 1e-9

    def _on_dose(self, message: DoseRate) -> None:
        rising = message.alert and not self.sep_alert
        self.sep_alert = message.alert
        if rising and self.phase not in SHELTER_PHASES:
            self._contingency(message)

    def _on_alert(self, message: Alert) -> None:
        # Only telemetry leak alerts; SEP is answered from /env/dose_rate (our own SEP_ALERT echoes here).
        if message.code != "SUIT_LEAK" or message.severity < Alert.WARNING:
            return
        if self.phase in SHELTER_PHASES or self.phase in (MissionState.BRIEFING, MissionState.PRECURSOR):
            return  # already going home, or nobody is outside yet
        self._set_phase(MissionState.CONTINGENCY, "SUIT_LEAK", "ReturnToShelter habitat",
                        ["continue EVA: the leaking suit's O2 margin shrinks with the leak factor"],
                        {"alert_id": message.alert_id, "leak_crew_ids": list(message.related_ids),
                         "alert_text": message.text})
        self._send_return()

    # --- transitions ------------------------------------------------------------------
    def _on_ev1(self, message: CrewState) -> None:
        p = message.pose.pose.position
        if (message.crew_id == "EV1" and message.header.frame_id == "map"
                and all(math.isfinite(v) for v in (p.x, p.y, p.z))):
            self._ev1_xy, self._ev1_receipt = (p.x, p.y), time.monotonic()
        else:
            self._ev1_xy, self._ev1_receipt = None, -math.inf

    def _on_advance(self, request, response):
        response.success = False
        if self._clock_pending:
            response.message = "clock start pending; wait for MissionState"
            return response
        # Orientation requests never override a real SEP contingency or its return.
        if self.sep_alert or self.task_ids:
            response.message = "shelter action/SEP has priority over orientation"
            return response
        try:
            next_phase, event = advance_intro(self.phase, self._ev1_xy,
                                             time.monotonic() - self._ev1_receipt, self.intro_locations)
        except ValueError as error:
            response.message = str(error)
            return response
        if self.phase == MissionState.BRIEFING:
            if not self._clock_control.services_are_ready():
                response.message = "mission clock service unavailable"
                return response
            self._clock_pending = True
            future = self._clock_control.set_parameters([Parameter("running", value=True)])
            def started(f):
                self._clock_pending = False
                try:
                    results = f.result().results
                    if (results and all(r.successful for r in results)
                            and self.phase == MissionState.BRIEFING and not self.sep_alert):
                        self._set_phase(next_phase, event, "orientation traverse", [],
                                        {"status": "SCENARIO", "science_product": False})
                except Exception as error:
                    self.get_logger().error(f"orientation clock start failed: {error}")
            future.add_done_callback(started)
            response.success, response.message = True, "accepted; wait for MissionState.TRAVERSE"
        else:
            self._set_phase(next_phase, event, "orientation context walkthrough", [],
                            {"status": "SCENARIO", "science_product": False})
            response.success, response.message = True, event
        return response

    # --- nominal flow (D015) -----------------------------------------------------------
    def _on_crew(self, crew_id: str, message: CrewState) -> None:
        p = message.pose.pose.position
        if message.header.frame_id == "map" and math.isfinite(p.x) and math.isfinite(p.y):
            self._crew_xy[crew_id] = (p.x, p.y)

    def _request_plan(self) -> None:
        if self._plan_pending or self.plan is not None or not self._plan_client.service_is_ready():
            return
        request = PlanEva.Request()
        request.site_id, request.objective = self.site_id, self.plan_objective
        request.crew_ids = list(self.crew_ids)
        request.max_duration_min = self.plan_max_min
        request.candidate_target_ids = list(self.plan_targets)
        self._plan_pending = True
        self._plan_client.call_async(request).add_done_callback(self._on_plan_response)

    def _on_plan_response(self, future) -> None:
        self._plan_pending = False
        response = future.result()
        if response is None or not response.success:
            self.get_logger().error(f"PlanEva failed: {getattr(response, 'message', 'no response')}",
                                    throttle_duration_sec=5.0)
            return
        self.plan = response.plan
        self.active_plan_id = response.plan.plan_id
        home = response.plan.route.poses[0].pose.position
        self.flow.shelter_xy = (home.x, home.y)

    def _start_clock(self) -> None:
        if self._clock_started or not self._scenario_client.service_is_ready():
            return
        request = ScenarioControl.Request()
        request.command = ScenarioControl.Request.START
        self._clock_started = True
        self._scenario_client.call_async(request)

    # --- precursor (T7, D015) ---------------------------------------------------------------
    def _on_known(self, delta: CellDelta) -> None:
        self._geometry = (delta.origin.x, delta.origin.y, delta.resolution_m)
        for c in delta.cells:
            if c.evidence_id:
                self._known_evidence.add(c.evidence_id)
            if c.state == 1 and c.speed_factor == 0.0 and c.evidence_id:
                self._known_blocked[(c.iy, c.ix)] = c.evidence_id

    def _on_decision(self, record: DecisionRecord) -> None:
        self._planner_evidence[record.decision_id] = list(record.evidence_ids)

    def _decide(self, context: str, chosen: str, candidates: list[str], evidence: list[str], assumptions: dict):
        self._decision_counter += 1
        record = DecisionRecord()
        record.header.stamp = self.get_clock().now().to_msg()
        record.decision_id = f"dec-{self.run_id or 'run'}-pre-{self._decision_counter:03d}"
        record.context, record.chosen = context, chosen
        record.candidates, record.evidence_ids = list(candidates), list(evidence)
        record.assumptions_json = json.dumps({"status": "SCENARIO", "pet_s": self.pet_s, **assumptions})
        record.model_version = "mission_manager precursor (D015)"
        self._decision_pub.publish(record)

    def _blocked_on_route(self, evidence: set[str]) -> list[tuple[int, int]]:
        if self._geometry is None:
            return []
        x0, y0, r = self._geometry
        route = [(q.pose.position.x, q.pose.position.y) for q in self.plan.route.poses]
        hits = []
        for (iy, ix), ev in sorted(self._known_blocked.items()):
            if ev not in evidence:
                continue
            cx, cy = x0 + (ix + 0.5) * r, y0 + (iy + 0.5) * r
            if any(math.hypot(cx - x, cy - y) <= self.route_clearance_m for x, y in route):
                hits.append((iy, ix))
        return hits

    def _precursor_tick(self) -> None:
        if self._pre_state == "wait":
            proposal = self._proposal
            if proposal is None or not self._scout.server_is_ready():
                return
            try:
                assumptions = json.loads(proposal.assumptions_json or "{}")
            except (TypeError, ValueError):
                self.get_logger().warning("invalid scout proposal JSON; waiting for a valid proposal",
                                          throttle_duration_sec=5.0)
                return
            if not isinstance(assumptions, dict):
                return
            area = assumptions.get("survey_area") or []
            if assumptions.get("plan_id") != self.active_plan_id or not isinstance(area, list) or len(area) < 3:
                return
            try:
                points = [Point32(x=float(x), y=float(y), z=0.0) for x, y in area]
                if not all(math.isfinite(p.x) and math.isfinite(p.y) for p in points):
                    return
            except (TypeError, ValueError, OverflowError):
                return
            goal = ExecuteScout.Goal()
            goal.request_id = f"scout-{self.run_id or 'run'}-{self._decision_counter + 1:04d}"
            goal.vehicle_id, goal.altitude_m = self.precursor_vehicle, 20.0
            goal.corridor.points = points
            self._pre_state = "flying"
            self._decide("robot_task_dispatch", goal.request_id, [proposal.chosen], [],
                         {"proposal": proposal.decision_id, "vehicle_id": goal.vehicle_id, "survey_area": area})
            try:
                self._scout.send_goal_async(goal).add_done_callback(self._on_scout_goal)
            except Exception as error:
                self._scout_incomplete(f"goal transport failed: {type(error).__name__}")
        elif self._pre_state == "settling":
            result = self._scout_result
            missing = set(result.evidence_ids) - self._known_evidence
            if missing:
                if time.monotonic() - self._scout_since < 5.0:
                    return  # Every returned observation must have reached cell_store.
                self._scout_incomplete("scout evidence not in cell-store snapshot", missing_count=len(missing))
                return
            # A blocked cell the scout did see counts even when the flight ended early (PARTIAL/FAILED).
            blocked = self._blocked_on_route(set(result.evidence_ids))
            if not blocked:
                outcome = SCOUT_OUTCOMES.get(int(result.outcome), str(int(result.outcome)))
                status = GOAL_STATUSES.get(self._scout_status, str(self._scout_status))
                verified = status == "SUCCEEDED" and outcome == "SUCCEEDED" and bool(result.evidence_ids)
                # An aborted goal returns a default Result whose outcome 0 reads SUCCEEDED with no
                # evidence: only a succeeded goal and outcome may declare the route clear.
                context = "precursor: route clear, plan kept" if verified else \
                    "precursor: survey incomplete, plan kept unverified"
                self._decide(context, self.active_plan_id, [self.active_plan_id], list(result.evidence_ids[:50]),
                             {"scout_outcome": outcome, "scout_status": status, "route_verified": verified,
                              "scout_reason": result.reason})
                if not verified:
                    self.get_logger().warning(f"scout ended {status}/{outcome} ({result.reason!r}); "
                                              "route not verified, plan kept")
                self._pre_state = "done" if verified else "incomplete"
                return
            self._replan = {"blocked": blocked, "evidence": sorted({self._known_blocked[c] for c in blocked}),
                            "old": self.plan, "pending": None}
            self._pre_state = "replanning"
        elif self._pre_state == "replanning":
            pending = self._replan["pending"]
            if pending is None:
                if self._plan_pending or not self._plan_client.service_is_ready():
                    return
                self._replan_attempts += 1
                request = PlanEva.Request()
                request.site_id, request.objective = self.site_id, self.plan_objective
                request.crew_ids = list(self.crew_ids)
                request.max_duration_min = self.plan_max_min
                request.candidate_target_ids = list(self.plan_targets)
                self._plan_pending = True
                self._plan_client.call_async(request).add_done_callback(self._on_replan_response)
                return
            seen = self._planner_evidence.get(pending.decision_id)
            if seen is None:
                return
            if set(self._replan["evidence"]) <= set(seen):
                old = self._replan["old"]
                self.plan, self.active_plan_id = pending, pending.plan_id
                margin = lambda plan: min((leg.return_margin_min for leg in plan.legs), default=math.nan)
                self._decide("replan after precursor", pending.plan_id, [old.plan_id, pending.plan_id],
                             self._replan["evidence"],
                             {"blocked_cells_on_route": [list(c) for c in self._replan["blocked"]],
                              "attempts": self._replan_attempts, "margin_v1_min": margin(old),
                              "margin_v2_min": margin(pending),
                              "stations_v1": [st.target_id for st in old.stations],
                              "stations_v2": [st.target_id for st in pending.stations]})
                self._pre_state = "done"
            elif self._replan_attempts >= self.evidence_retries:
                self._decide("replan failed: scout evidence not applied, plan kept", self.active_plan_id,
                             [self.active_plan_id], self._replan["evidence"], {"attempts": self._replan_attempts})
                self._pre_state = "done"
            else:
                self._replan["pending"] = None  # ask again: the planner has not applied the evidence yet

    def _on_scout_goal(self, future) -> None:
        if self.phase != MissionState.PRECURSOR or self._pre_state != "flying":
            return
        try:
            handle = future.result()
            if handle is None or not handle.accepted:
                self._scout_incomplete("scout goal rejected or absent")
                return
            handle.get_result_async().add_done_callback(self._on_scout_result)
        except Exception as error:
            self._scout_incomplete(f"scout goal response failed: {type(error).__name__}")

    def _on_scout_result(self, future) -> None:
        if self.phase != MissionState.PRECURSOR or self._pre_state != "flying":
            return
        try:
            wrapped = future.result()
            if wrapped is None or wrapped.result is None:
                self._scout_incomplete("scout result absent")
                return
            self._scout_result, self._scout_status = wrapped.result, int(wrapped.status)
        except Exception as error:
            self._scout_incomplete(f"scout result transport failed: {type(error).__name__}")
            return
        result = self._scout_result
        if (self._scout_status != GoalStatus.STATUS_SUCCEEDED or result.outcome not in
                (ExecuteScout.Result.SUCCEEDED, ExecuteScout.Result.PARTIAL) or not result.evidence_ids or
                any(not value for value in result.evidence_ids) or len(set(result.evidence_ids)) != len(result.evidence_ids)):
            self._scout_incomplete(result.reason or "scout did not return a usable successful/partial survey",
                                   scout_status=GOAL_STATUSES.get(self._scout_status, str(self._scout_status)),
                                   scout_outcome=SCOUT_OUTCOMES.get(int(result.outcome), str(result.outcome)))
            return
        self._scout_since = time.monotonic()
        self._pre_state = "settling"

    def _scout_incomplete(self, reason: str, **details) -> None:
        """Hold PRECURSOR; absence/failure of a survey is never proof of a clear route."""
        self._pre_state = "incomplete"
        self._decide("precursor: survey incomplete, plan kept unverified", self.active_plan_id,
                     [self.active_plan_id], [], {"route_verified": False, "scout_reason": reason, **details})
        self.get_logger().warning(f"PRECURSOR held: {reason}")

    def _on_replan_response(self, future) -> None:
        self._plan_pending = False
        response = future.result()
        if response is None or not response.success:
            self.get_logger().error(f"replan failed: {getattr(response, 'message', 'no response')}")
            return
        self._replan["pending"] = response.plan

    def _flow_tick(self) -> None:
        if self.phase == MissionState.BRIEFING and self.plan is None:
            self._request_plan()
        if self.phase == MissionState.PRECURSOR and self.precursor:
            self._precursor_tick()
        if self.flow.schedule is not None:
            self._start_clock()
        if self.phase == MissionState.CONTINGENCY or self.task_ids:
            return  # the contingency path owns the phase
        pet = self.pet_s if math.isfinite(self.pet_s) else self.egress_pet_s
        step = self.flow.step(self.phase, pet, self._crew_xy, plan_ready=self.plan is not None,
                              precursor_done=self._pre_state == "done")
        if step is None:
            return
        phase, context = step
        if phase == MissionState.TRAVERSE and self.flow.schedule is None:
            self.flow.begin(schedule_from_plan(self.plan, self.egress_pet_s))
            self._start_clock()
        self._set_phase(phase, context, self.active_plan_id, [], {"status": "SCENARIO", "plan_id": self.active_plan_id})

    def _set_phase(self, phase: int, context: str, chosen: str, reasons: list[str], evidence: dict) -> None:
        previous, self.phase = self.phase, phase
        self.transitions.append((self.pet_s, previous, phase))
        self.counter += 1
        record = DecisionRecord()
        record.header.stamp = self.get_clock().now().to_msg()
        record.decision_id = f"dec-{self.run_id or 'run'}-{self.counter:04d}"
        record.context = context
        record.chosen = chosen
        record.rejected_reasons = reasons
        record.assumptions_json = json.dumps({"pet_s": self.pet_s, "from_phase": previous, "to_phase": phase,
                                              **evidence})
        record.model_version = "mission_manager nominal flow (D015) + SEP contingency (D012)"
        self._decision_pub.publish(record)
        self._publish_state()

    def _contingency(self, dose: DoseRate) -> None:
        detector = dose.alert_detector
        value = dose.dose_rate_e_ugy_h if detector == "E" else dose.dose_rate_b_ugy_h
        background = dose.background_e_ugy_h if detector == "E" else dose.background_b_ugy_h
        alert = Alert()
        alert.header.stamp = self.get_clock().now().to_msg()
        alert.alert_id = f"alert-{self.run_id or 'run'}-sep-{self.counter + 1:04d}"
        alert.severity = Alert.EMERGENCY
        alert.code = "SEP_ALERT"
        alert.text = (f"SEP alarm on RAD {detector}: {value:.2f} uGy/h vs background {background:.2f} "
                      f"(sol {dose.source_sol}). Return to shelter.")
        alert.related_ids = list(self.crew_ids)
        self._alert_pub.publish(alert)
        self._set_phase(MissionState.CONTINGENCY, "SEP_ALERT", "ReturnToShelter habitat",
                        ["continue EVA: violates FR-03/FR-04 during a SEP alarm"],
                        {"detector": detector, "dose_ugy_h": value, "background_ugy_h": background,
                         "source_sol": dose.source_sol, "source_file": dose.source_file})
        self._send_return()

    def _send_return(self) -> None:
        if not self._rts.server_is_ready():
            self.get_logger().error("ReturnToShelter server is not available; crew must be told directly")
            return
        goal = ReturnToShelter.Goal()
        goal.request_id = f"rts-{self.run_id or 'run'}-{self.counter:04d}"
        goal.crew_ids = list(self.crew_ids)
        goal.shelter_id = "habitat"
        goal.rover_meets_crew = False
        self._rts.send_goal_async(goal).add_done_callback(lambda f, rid=goal.request_id: self._on_goal(f, rid))

    def _on_goal(self, future, request_id: str) -> None:
        handle = future.result()
        if not handle.accepted:
            self.get_logger().error("ReturnToShelter goal rejected")
            return
        self.task_ids = [request_id]
        self._set_phase(MissionState.RETURN, "RETURN_STARTED", request_id, [], {"request_id": request_id})
        handle.get_result_async().add_done_callback(self._on_result)

    def _on_result(self, future) -> None:
        wrapped = future.result()
        result = wrapped.result
        if wrapped.status == GoalStatus.STATUS_SUCCEEDED and result.outcome == ReturnToShelter.Result.SUCCEEDED:
            self.task_ids = []
            self._set_phase(MissionState.DEBRIEF, "CREW_IN_SHELTER", "debrief", [],
                            {"actual_time_min": result.actual_time_min})
        else:
            self.get_logger().error(f"ReturnToShelter ended with outcome {result.outcome}: {result.reason}")

    def _publish_state(self) -> None:
        message = MissionState()
        message.header.stamp = self.get_clock().now().to_msg()
        message.run_id, message.scenario_id = self.run_id, self.scenario_id
        message.phase = self.phase
        message.active_task_ids = list(self.task_ids)
        message.active_plan_id = self.active_plan_id
        message.pet_min = self.pet_s / 60.0 if math.isfinite(self.pet_s) else 0.0
        self._state_pub.publish(message)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = MissionManagerNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
