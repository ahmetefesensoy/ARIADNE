import importlib.util
from pathlib import Path

spec=importlib.util.spec_from_file_location('cmd_watchdog',Path(__file__).parents[1]/'scripts/cmd_watchdog.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


def test_stale_invalid_or_excessive_commands_are_bounded():
    assert module.gated(1,2,.1)==(.4,.5)
    assert module.gated(-1,-2,.1)==(-.4,-.5)
    assert module.gated(.2,.3,.49)==(.2,.3)
    assert module.gated(.2,.3,.51)==(0.,0.)
    for value in (float('nan'),float('inf')):assert module.gated(value,.2,.1)==(0.,0.)


def test_live_watchdog_stops_after_command_stream_disappears():
    import time
    import rclpy
    from rclpy.executors import SingleThreadedExecutor
    from rclpy.node import Node
    from geometry_msgs.msg import Twist
    rclpy.init();gate=module.Watchdog();peer=Node('watchdog_test_peer')
    observed=[]
    sub=peer.create_subscription(Twist,'/rover_1/cmd_vel_sim',lambda msg:observed.append(msg.linear.x),10)
    pub=peer.create_publisher(Twist,'/rover_1/cmd_vel',10)
    executor=SingleThreadedExecutor();executor.add_node(gate);executor.add_node(peer)
    try:
        deadline=time.monotonic()+3
        while pub.get_subscription_count()<1 and time.monotonic()<deadline:executor.spin_once(timeout_sec=.05)
        assert pub.get_subscription_count()==1
        command=Twist();command.linear.x=.2
        while time.monotonic()<deadline and .2 not in observed:
            pub.publish(command);executor.spin_once(timeout_sec=.05)
        assert .2 in observed
        deadline=time.monotonic()+.9
        while time.monotonic()<deadline:executor.spin_once(timeout_sec=.05)
        assert observed[-1]==0
    finally:
        executor.shutdown();gate.destroy_node();peer.destroy_node();rclpy.try_shutdown()
