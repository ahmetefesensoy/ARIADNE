"""Exercise generated REDLINE interfaces, not a duplicate Python schema."""

from array import array
import base64
import math

import pytest
from builtin_interfaces.msg import Time
from geometry_msgs.msg import Point, Point32, Polygon, PoseStamped
from rclpy.serialization import deserialize_message, serialize_message
from rosidl_runtime_py.utilities import get_action, get_message, get_service

from redline_msgs.msg import (
    CellState,
    DoseRate,
    EVAPlan,
    EvidenceRecord,
    FieldTile,
    MarginField,
    PlanLeg,
    Provenance,
    RedLine,
    SampleRecord,
    ScalarField,
    Station,
)
from redline_msgs.srv import PlanEva, QueryCell, ScenarioControl, SetCommandOwner


MESSAGE_NAMES = [
    "FieldTile",
    "Provenance",
    "CellState",
    "CellDelta",
    "ScalarField",
    "MarginField",
    "RedLine",
    "Consumables",
    "CrewState",
    "Station",
    "PlanLeg",
    "EVAPlan",
    "Alert",
    "RuleViolation",
    "DoseRate",
    "EnvState",
    "EvidenceRecord",
    "InstrumentProduct",
    "SampleRecord",
    "DecisionRecord",
    "CommandOwner",
    "MissionState"
]
SERVICE_NAMES = [
    "SetCommandOwner",
    "PlanEva",
    "QueryCell",
    "ScenarioControl",
    "GetManifest",
    "MissionCommand",
    "AnalyzeSample"
]
ACTION_NAMES = [
    "SurveyArea",
    "InspectTarget",
    "ContactScience",
    "RemoteLibs",
    "MultispectralImage",
    "NeutronSurvey",
    "Drill",
    "CacheSample",
    "DeployStation",
    "ReturnToShelter",
    "ExecuteScout",
    "CollectSample"
]
OUTCOME_NAMES = ("SUCCEEDED", "PARTIAL", "CANCELED", "FAILED", "REJECTED")


def roundtrip(message):
    """Invoke the built C typesupport and CDR codec on a generated instance."""
    return deserialize_message(serialize_message(message), type(message))


@pytest.mark.parametrize("name", MESSAGE_NAMES)
def test_every_message_resolves_and_serializes(name):
    interface = get_message(f"redline_msgs/msg/{name}")
    message = interface()
    assert roundtrip(message) == message


@pytest.mark.parametrize("name", SERVICE_NAMES)
@pytest.mark.parametrize("part", ["Request", "Response"])
def test_every_service_payload_resolves_and_serializes(name, part):
    interface = get_service(f"redline_msgs/srv/{name}")
    message = getattr(interface, part)()
    assert roundtrip(message) == message


@pytest.mark.parametrize("name", ACTION_NAMES)
@pytest.mark.parametrize("part", ["Goal", "Result", "Feedback"])
def test_every_action_payload_resolves_and_serializes(name, part):
    interface = get_action(f"redline_msgs/action/{name}")
    message = getattr(interface, part)()
    assert roundtrip(message) == message


@pytest.mark.parametrize("name", ACTION_NAMES)
def test_every_action_protocol_wrapper_has_typesupport(name):
    interface = get_action(f"redline_msgs/action/{name}")
    wrappers = (
        interface.Impl.SendGoalService.Request(),
        interface.Impl.SendGoalService.Response(),
        interface.Impl.GetResultService.Request(),
        interface.Impl.GetResultService.Response(),
        interface.Impl.FeedbackMessage(),
    )
    for message in wrappers:
        assert roundtrip(message) == message


@pytest.mark.parametrize("name", ACTION_NAMES)
def test_common_application_outcomes_are_not_ros_goal_statuses(name):
    interface = get_action(f"redline_msgs/action/{name}")
    assert [getattr(interface.Result, key) for key in OUTCOME_NAMES] == list(range(5))
    for code in range(5):
        result = interface.Result(outcome=code, reason="contract roundtrip")
        assert roundtrip(result).outcome == code


def test_binary_tile_preserves_png_and_georeference():
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8"
        "/x8AAwMCAO+a9e0AAAAASUVORK5CYII="
    )
    tile = FieldTile(
        site_id="BXW",
        name="margin_min_EV1",
        unit="min",
        resolution_m=4.0,
        origin=Point(x=-40.0, y=80.0, z=2.5),
        width=1,
        height=1,
        scale=0.5,
        offset=-10.0,
        nodata_byte=255,
        png=array("B", png),
    )
    tile.header.frame_id = "map"
    tile.header.stamp = Time(sec=10, nanosec=123)
    decoded = roundtrip(tile)
    assert bytes(decoded.png) == png
    assert decoded.origin == tile.origin
    assert decoded.header == tile.header
    assert decoded.resolution_m == 4.0
    assert (decoded.width, decoded.height, decoded.nodata_byte) == (1, 1, 255)
    assert decoded.scale == 0.5 and decoded.offset == -10.0


def test_unknown_raster_cells_preserve_nan_not_zero():
    field = ScalarField(
        site_id="BXW",
        name="slope",
        unit="deg",
        resolution_m=4.0,
        width=2,
        height=1,
        data=array("f", [math.nan, 12.5]),
        sigma=array("f", [math.nan, 2.0]),
        provenance=Provenance(
            status=Provenance.DERIVED,
            product_id="fixture-dem",
            note="Synthetic serialization fixture; not a Mars measurement",
        ),
    )
    decoded = roundtrip(field)
    assert math.isnan(decoded.data[0]) and math.isnan(decoded.sigma[0])
    assert decoded.data[1] == 12.5 and decoded.sigma[1] == 2.0
    assert decoded.provenance.status == Provenance.DERIVED


def test_margin_and_regions_keep_limiting_crew_and_resource():
    margin = MarginField(
        site_id="BXW",
        crew_id="EV2",
        resolution_m=4.0,
        width=2,
        height=1,
        margin_min=array("f", [3.5, math.nan]),
        limiting=array("B", [MarginField.LIM_O2, MarginField.LIM_SHELTER]),
        terminate_threshold_min=5.0,
    )
    decoded_margin = roundtrip(margin)
    assert decoded_margin.crew_id == "EV2"
    assert decoded_margin.margin_min[0] == 3.5
    assert math.isnan(decoded_margin.margin_min[1])
    assert list(decoded_margin.limiting) == [MarginField.LIM_O2, MarginField.LIM_SHELTER]
    region = Polygon(points=[
        Point32(x=0.0, y=0.0, z=0.0),
        Point32(x=4.0, y=0.0, z=0.0),
        Point32(x=0.0, y=4.0, z=0.0),
    ])
    line = RedLine(
        site_id="BXW",
        abort_regions=[region],
        terminate_regions=[],
        limiting_crew_id="EV2",
        limiting_consumable=MarginField.LIM_O2,
        margin_now_min=3.5,
    )
    decoded_line = roundtrip(line)
    assert decoded_line.abort_regions[0].points[1].x == 4.0
    assert decoded_line.terminate_regions == []
    assert decoded_line.limiting_crew_id == "EV2"
    assert decoded_line.limiting_consumable == MarginField.LIM_O2


def test_measurement_receipt_and_publication_times_stay_distinct():
    evidence = EvidenceRecord(
        evidence_id="ev-fixture-001",
        measured=Time(sec=20, nanosec=1),
        received=Time(sec=21, nanosec=2),
        source="fixture_sensor",
        provenance=Provenance(
            status=Provenance.SIMULATED,
            product_id="sim-fixture-sensor-001",
            version="fixture-1",
        ),
        quality=0.5,
        input_ids=["fixture-input"],
        payload_uri="fixture://sensor",
        summary_json='{"fixture":true}',
    )
    evidence.header.stamp = Time(sec=22, nanosec=3)
    decoded = roundtrip(evidence)
    assert (decoded.measured.sec, decoded.received.sec, decoded.header.stamp.sec) == (
        20, 21, 22
    )
    assert decoded.provenance.status == Provenance.SIMULATED
    assert decoded.input_ids == ["fixture-input"]
    dose = DoseRate(
        source_sol=4190,
        historical_utc=Time(sec=1716185719),
        alert=True,
        alert_detector="E",
    )
    dose.header.stamp = Time(sec=22)
    decoded_dose = roundtrip(dose)
    assert decoded_dose.source_sol == 4190
    assert decoded_dose.historical_utc.sec == 1716185719
    assert decoded_dose.header.stamp.sec == 22


def test_sample_origin_is_not_analysis_location():
    sample = SampleRecord(
        sample_id="smp-BXW-fixture",
        target_id="fixture-target",
        origin_point=Point(x=10.0, y=20.0, z=1.0),
        analysis_point=Point(x=25.0, y=40.0, z=2.0),
        tool="fixture-tool",
        container_id="fixture-container",
        state=SampleRecord.RECORDED,
        evidence_ids=["ev-fixture-001"],
    )
    decoded = roundtrip(sample)
    assert decoded.origin_point.x == 10.0
    assert decoded.analysis_point.x == 25.0
    assert decoded.origin_point != decoded.analysis_point
    assert decoded.state == SampleRecord.RECORDED


def test_nested_plan_service_and_cell_evidence_survive_cdr():
    plan = EVAPlan(
        plan_id="fixture-plan",
        version=1,
        site_id="BXW",
        crew_ids=["EV1", "EV2"],
        stations=[Station(
            station_id="fixture-station",
            target_id="fixture-target",
            position=Point(x=4.0, y=8.0),
            service_min=2.0,
            tasks=["PHOTO"],
        )],
        legs=[PlanLeg(from_id="habitat", to_id="fixture-station", duration_min=3.0)],
        total_duration_min=5.0,
        decision_id="fixture-decision",
    )
    plan.route.header.frame_id = "map"
    pose = PoseStamped()
    pose.pose.orientation.w = 1.0
    pose.pose.position = Point(x=4.0, y=8.0)
    plan.route.poses = [pose]
    response = roundtrip(PlanEva.Response(success=True, plan=plan))
    assert response.success and response.plan == plan
    query = QueryCell.Response(
        found=True,
        cell=CellState(ix=1, iy=2, state=CellState.NOT_DETECTED_LIMITED),
        evidence=[EvidenceRecord(evidence_id="ev-fixture-001")],
    )
    decoded_query = roundtrip(query)
    assert decoded_query.cell.state == CellState.NOT_DETECTED_LIMITED
    assert decoded_query.evidence[0].evidence_id == "ev-fixture-001"


def test_commands_distinguish_acceptance_from_requested_state():
    request = SetCommandOwner.Request(
        vehicle_id="rover_1", requested_owner=2, reason="fixture"
    )
    response = SetCommandOwner.Response(
        accepted=False, current_owner=3, message="fixture safety stop"
    )
    assert roundtrip(request).requested_owner == 2
    decoded = roundtrip(response)
    assert not decoded.accepted and decoded.current_owner == 3
    seek = ScenarioControl.Request(
        command=ScenarioControl.Request.SEEK,
        scenario_id="fixture",
        time_scale=2.0,
        seek_s=120.0,
    )
    assert roundtrip(seek).command == ScenarioControl.Request.SEEK
    assert roundtrip(seek).seek_s == 120.0


@pytest.mark.parametrize("status", [0, 1, 2, 3])
def test_all_provenance_categories_survive_serialization(status):
    provenance = Provenance(status=status, product_id="fixture")
    assert roundtrip(provenance).status == status
