"""Player-directed SCENARIO EVA. Results, not interaction presses, finish tasks.

This layer records intent/progress; physics, measurement models and resources
remain in their own ROS/core components. No NASA science value is invented here.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math


@dataclass(frozen=True)
class CampaignTask:
    id: str
    title: str
    instruction: str
    kind: str
    actor: str
    target_id: str
    xy: tuple[float, float]
    phase: int
    radius_m: float = 4.0

    @property
    def remote_command(self):
        # EV1 stays observable, but need not stand beside a robot's target.
        # Pre-egress scout preparation deliberately remains at command.
        return self.actor == "rover_1"


def campaign_tasks(branch: str = "ridge", locations=None) -> tuple[CampaignTask, ...]:
    if branch not in ("ridge", "hollow"):
        raise ValueError("unknown science route")
    target = "BXW_RIDGE_A" if branch == "ridge" else "BXW_HOLLOW_B"
    field = (306., -454.) if branch == "ridge" else (320., -448.)
    if locations is not None:
        point=locations.get(target)
        if point is None or len(point)!=2 or not all(math.isfinite(v) for v in point):
            raise ValueError("finite registered field target required")
        field=tuple(float(v) for v in point)
    return (
        CampaignTask("briefing", "01 / Çıkış brifingi", "Komuta panosunda soruyu, giysiyi ve dönüş payını incele; E ile keşif hazırlığına geç.", "briefing", "EV1", "COMMAND", (285.1, -456.), 0),
        CampaignTask("scout", "02 / Öncü drone keşfi", "Komutadan E ile keşfi başlat. Gözlem kanıtı gelmeden saha kararı açılmaz.", "scout", "scout_1", "CORRIDOR", (285.1, -456.), 1),
        CampaignTask("route", "03 / Saha kararı", "M panosunda 1: sırt, 2: çukur rotasını seç. Gözlemi ve belirsizliği birlikte değerlendir.", "decision", "EV1", "COMMAND", (285.1, -456.), 0),
        CampaignTask("collect", "04 / Yüzey numunesini al", "Hedefin 2,5 m yakınına git; E ile aleti indirme, toplama ve kaba alma işlemini başlat.", "collect", "EV1", target, field, 2, 2.5),
        CampaignTask("xrf", "05 / El tipi temas ölçümü", "Aynı hedefte E ile ölçümü başlat. Hata çubuklu bileşim ürünü tamamlandığında kaydedilir.", "xrf", "EV1", target, field, 3, 2.5),
        CampaignTask("weather", "06 / Çevre istasyonunu yerleştir", "Hedefte E ile doz istasyonunu yerleştir; istasyon kimliği ve konumu kayda girer.", "weather", "EV1", target, field, 3, 3.0),
        CampaignTask("rover_libs", "07 / Rover hedef incelemesi", "Tabletten E ile roverı uzaktan hedefe gönder. Nav2 varışı doğrular, ardından LIBS ölçümü yürür.", "libs", "rover_1", target, field, 3),
        CampaignTask("rover_dan", "08 / Yeraltı hidrojen taraması", "Tabletten E ile DAN taramasını uzaktan başlat. WEH ve belirsizlik ürünü veri panosuna gelir.", "dan", "rover_1", target, field, 3),
        CampaignTask("drill", "09 / Sondaj ve arıza yönetimi", "Tabletten E ile sondajı uzaktan başlat. Elde edilen derinlik ve varsa arıza ürün sonucuyla gösterilir.", "drill", "rover_1", target, field, 3),
        CampaignTask("cache", "10 / Laboratuvara numune teslimi", "Bilim hazırlık odasına dön. E ile kabı teslim et; numune kökeni ve analiz yeri ayrı tutulur.", "cache", "EV1", "LAB", (285.1, -468.), 4),
        CampaignTask("assessment", "11 / Veriye göre karar", "Komuta ekranında ürünleri ve hata çubuklarını incele. 1: örüntü desteği, 2: ek ölçüm gerekiyor.", "assessment", "EV1", "COMMAND", (285.1, -456.), 3),
        CampaignTask("debrief", "12 / Dönüş ve debrief", "Komutada E ile EVA kaydını kapat. Numuneler, ürünler ve karar gerekçeleri kalır.", "debrief", "EV1", "COMMAND", (285.1, -456.), 4),
    )


class Campaign:
    def __init__(self, locations=None):
        self.locations=locations
        campaign_tasks(locations=locations)
        campaign_tasks("hollow",locations)
        self.branch = "ridge"
        self.index = 0
        self.revision = 0
        self.state = "ready"
        self.operation_id = ""
        self.progress = 0.
        self.operation_phase = ""
        self.message = "Brifing bekleniyor."
        self.completed: list[str] = []
        self.product_ids: list[str] = []
        self.evidence_ids: list[str] = []
        self.sample_ids: list[str] = []
        self.decisions: list[dict] = []
        self.requests: dict[str, tuple[str, str, int]] = {}

    @property
    def tasks(self):
        return campaign_tasks(self.branch,self.locations)

    @property
    def task(self):
        return self.tasks[min(self.index, len(self.tasks) - 1)]

    @property
    def done(self):
        return self.index >= len(self.tasks)

    def validate_command(self, request_id: str, command: str, target: str, revision: int,
                         position, age_s: float):
        if not request_id or len(request_id) > 96:
            raise ValueError("valid request_id required")
        fingerprint = (command, target, revision)
        if request_id in self.requests:
            if self.requests[request_id] != fingerprint:
                raise ValueError("request_id reused for a different command")
            return False  # duplicate acknowledgement never re-executes
        if len(self.requests) >= 4096:
            raise ValueError("command ledger full; start a new run")
        if revision != self.revision:
            raise ValueError("görev değişti; güncel panoyu bekle")
        if self.done:
            raise ValueError("EVA kaydı kapalı")
        if target != self.task.target_id:
            raise ValueError("etkin görev hedefi eşleşmiyor")
        if command == "CANCEL":
            if self.state not in ("pending", "running"):
                raise ValueError("iptal edilecek etkin işlem yok")
            return True
        if self.state in ("pending", "running"):
            raise ValueError("işlem sürüyor; sonucu bekle veya iptal et")
        if (position is None or len(position) != 2 or not all(math.isfinite(v) for v in position)
                or not math.isfinite(age_s) or not 0 <= age_s <= 2):
            raise ValueError("güncel EV1 konumu gerekli")
        if not self.task.remote_command and math.dist(position, self.task.xy) > self.task.radius_m:
            raise ValueError(f"önce etkin görev noktasına yaklaş ({self.task.radius_m:g} m)")
        options = {"decision": {"CHOOSE_RIDGE", "CHOOSE_HOLLOW"},
                   "assessment": {"SUPPORT_PATTERN", "NEED_MORE_DATA"}}
        allowed = options.get(self.task.kind, {"START"})
        if command not in allowed:
            raise ValueError("bu görev açık bir karar gerektiriyor; M panosunu aç")
        return True

    def accept(self, request_id, command, target, revision):
        self.requests[request_id] = (command, target, revision)
        self.operation_id = request_id
        self.state = "pending"
        self.progress = 0.
        self.operation_phase = "QUEUED"
        self.message = "Komut kabul edildi; yürütme sonucu bekleniyor."
        self.revision += 1

    def decide(self, command):
        if self.task.kind == "decision":
            self.branch = "ridge" if command == "CHOOSE_RIDGE" else "hollow"
        self.decisions.append({"task_id": self.task.id, "chosen": command,
                               "evidence_ids": self.evidence_ids[-100:], "product_ids": self.product_ids[-100:]})
        self.finish(success=True)

    def feedback(self, phase: str, progress: float):
        if self.state not in ("pending", "running"):
            return
        if not math.isfinite(progress) or not 0 <= progress <= 1:
            raise ValueError("finite bounded operation progress required")
        self.state, self.operation_phase, self.progress = "running", str(phase)[:96], max(self.progress,progress)

    def finish(self, *, success: bool, products=(), evidence=(), samples=(), reason=""):
        if self.state not in ("pending", "running"):
            raise ValueError("no accepted operation to finish")
        if success:
            kind = self.task.kind
            if kind == "scout" and not evidence:
                raise ValueError("scout result requires observation evidence")
            if kind in ("collect", "xrf", "libs", "dan", "drill", "weather") and not (products or samples):
                raise ValueError("science result requires persisted products or sample")
            if kind in ("collect", "drill", "cache") and not samples:
                raise ValueError("sample operation requires a sample record")
            self.completed.append(self.task.id)
            self.product_ids.extend(p for p in products if p not in self.product_ids)
            self.evidence_ids.extend(e for e in evidence if e not in self.evidence_ids)
            self.sample_ids.extend(s for s in samples if s not in self.sample_ids)
            self.index += 1
            self.state = "complete" if self.done else "ready"
            self.progress = 1. if self.done else 0.
            self.operation_phase = "COMPLETE" if self.done else "READY"
            self.message = "EVA kaydı tamamlandı." if self.done else "İşlem kaydedildi. Sonraki görevi incele."
        else:
            self.state, self.message = "failed", reason[:240] or "İşlem tamamlanmadı; görev açık."
        self.revision += 1

    def snapshot(self, position=None, position_age_s=math.inf):
        pose_fresh = (position is not None and len(position) == 2
                      and all(math.isfinite(v) for v in position)
                      and math.isfinite(position_age_s) and 0 <= position_age_s <= 2)
        endpoints = {
            "scout": ("/scout_1/execute_scout", "ExecuteScout"),
            "collect": ("/redline/science/collect_sample", "CollectSample"),
            "xrf": ("/rover_1/contact_science", "ContactScience"),
            "libs": ("/rover_1/remote_libs", "RemoteLibs"),
            "dan": ("/rover_1/neutron_survey", "NeutronSurvey"),
            "drill": ("/rover_1/drill", "Drill"),
            "cache": ("/redline/science/cache_sample", "CacheSample"),
            "weather": ("/redline/science/deploy_station", "DeployStation"),
        }
        tasks = []
        for index, task in enumerate(self.tasks):
            complete = task.id in self.completed
            active = not self.done and index == self.index
            state = "complete" if complete else "active" if active else "locked"
            distance = math.dist(position, task.xy) if pose_fresh else None
            arrived = pose_fresh and distance <= task.radius_m
            location_ready = bool(pose_fresh and (task.remote_command or arrived))
            busy = active and self.state in ("pending", "running")
            enabled = active and location_ready and not busy
            blocked = ("completed" if complete else "locked" if not active else "crew_pose_stale" if not pose_fresh
                       else "approach_site" if not location_ready else "operation_running" if busy else "")
            endpoint, action = endpoints.get(task.kind, ("/redline/campaign/command", "MissionCommand"))
            record = asdict(task)
            record["presentation"] = {"state": state, "site_xy_m": list(task.xy), "actor": task.actor,
                "endpoint": endpoint, "action": action, "command_endpoint": "/redline/campaign/command",
                "interaction_mode": "remote" if task.remote_command else "local",
                "requires_proximity": not task.remote_command, "crew_pose_fresh": bool(pose_fresh),
                "distance_m": distance, "arrived": bool(arrived), "location_ready": location_ready,
                "enabled": bool(enabled), "blocked_reason": blocked}
            if task.kind == "libs":
                record["presentation"]["navigation_endpoint"] = "/rover_1/navigate_to_pose"
            tasks.append(record)
        return {"schema": "redline.campaign.v1", "status": "SCENARIO", "revision": self.revision,
                "task_index": self.index, "task_count": len(self.tasks), "task": tasks[min(self.index, len(tasks) - 1)],
                "tasks": tasks, "completed": self.completed,
                "state": self.state, "operation_id": self.operation_id, "operation_phase": self.operation_phase,
                "progress": self.progress, "message": self.message, "branch": self.branch,
                "product_ids": self.product_ids[-100:], "evidence_ids": self.evidence_ids[-100:],
                "sample_ids": self.sample_ids[-50:], "decisions": self.decisions[-20:], "done": self.done}
