"""Flight readiness gates with injected Gazebo transport; not a flight acceptance."""
import time
import math
import pytest
import rclpy
from geometry_msgs.msg import Point, Point32,PoseStamped
from rclpy.action import GoalResponse
from rclpy.parameter import Parameter
from redline_env.scout_flight import ScoutFlightNode, PhysicsPose
from redline_msgs.action import ExecuteScout
from redline_msgs.msg import MissionState, CrewState


class Publisher:
    def __init__(self):self.messages=[]
    def publish(self, message):self.messages.append(message)

class Transport:
    def subscribe(self, *args): return True
    def advertise(self, *args): return Publisher()


@pytest.fixture
def node():
    rclpy.init()
    flight=None
    try:
        flight=ScoutFlightNode(transport_factory=Transport,parameter_overrides=[Parameter("origin_map_xyz",value=[40.,0.,0.])])
        now=time.monotonic()
        flight._pose=PhysicsPose(1.,(40.,0.,1.),(0.,0.,0.,1.),(0.,0.,0.),now)
        phase=MissionState(phase=MissionState.PRECURSOR);flight._on_phase(phase)
        crew=PoseStamped();crew.header.frame_id="map";crew.pose.orientation.w=1.;flight._on_crew("EV1",crew)
        yield flight
    finally:
        if flight:flight.destroy_node()
        rclpy.try_shutdown()


def goal():
    g=ExecuteScout.Goal(request_id="flight-test",vehicle_id="scout_1",altitude_m=2.,max_flight_s=60.)
    g.corridor.points=[Point32(x=40.,y=0.),Point32(x=43.,y=0.),Point32(x=43.,y=3.),Point32(x=40.,y=3.)]
    return g


def test_accepts_only_fresh_precursor_and_deduplicates(node):
    assert node._accept(goal())==GoalResponse.ACCEPT
    assert node._accept(goal())==GoalResponse.REJECT


@pytest.mark.parametrize("failure",["phase","crew_stale","pose_stale","crew_near","range","nan"])
def test_flight_rejected_without_gates(node,failure):
    g=goal()
    if failure=="phase":node._phase=MissionState.TRAVERSE
    elif failure=="crew_stale":node._crew["EV1"]=((0.,0.,0.),time.monotonic()-10)
    elif failure=="pose_stale":node._pose=PhysicsPose(1.,(40.,0.,1.),(0.,0.,0.,1.),(0.,0.,0.),time.monotonic()-5)
    elif failure=="crew_near":node._crew["EV1"]=((35.,0.,0.),time.monotonic())
    elif failure=="range":g.corridor.points[0].x=500.
    elif failure=="nan":g.altitude_m=float("nan")
    assert node._accept(g)==GoalResponse.REJECT


def test_safe_checks_phase_during_flight_not_only_goal_acceptance(node):
    assert node._safe()[0]
    node._phase=MissionState.RETURN
    assert not node._safe()[0]


def test_tilted_aircraft_gets_full_body_velocity_not_yaw_only(node):
    node._pose=PhysicsPose(2.,(40.,0.,1.),(0.,math.sin(math.pi/8),0.,math.cos(math.pi/8)),(0.,0.,0.),time.monotonic())
    node._command((0.,0.,1.5))
    command=node._commands.messages[-1]
    assert command.linear.x==pytest.approx(-1.5/math.sqrt(2))
    assert command.linear.z==pytest.approx(1.5/math.sqrt(2))
    assert command.angular.z==0
