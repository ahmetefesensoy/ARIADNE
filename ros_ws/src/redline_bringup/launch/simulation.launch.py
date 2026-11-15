"""T3 Gazebo + bridge + robot frames, without T2 planner dependencies."""
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, EmitEvent, ExecuteProcess, OpaqueFunction, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.conditions import IfCondition
from launch.events import Shutdown
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def setup(context):
    share=Path(get_package_share_directory('redline_bringup'))
    description=Path(get_package_share_directory('redline_description'))
    world=Path(LaunchConfiguration('world').perform(context))
    urdf=Path(LaunchConfiguration('robot_urdf').perform(context))
    if not world.is_file():raise ValueError('Existing generated world path is required')
    gazebo=ExecuteProcess(cmd=['gz','sim','-s','-r','--headless-rendering','-v','3',str(world)],output='screen')
    watchdog=Node(package='redline_bringup',executable='cmd_watchdog.py',output='screen',parameters=[{'use_sim_time':True}])
    return [
        gazebo,
        RegisterEventHandler(OnProcessExit(target_action=gazebo,
            on_exit=[EmitEvent(event=Shutdown(reason='Gazebo server exited'))])),
        Node(package='ros_gz_bridge',executable='parameter_bridge',name='gazebo_bridge',
             parameters=[{'config_file':str(share/'config/bridge.yaml'),'use_sim_time':True}],output='screen'),
        Node(package='robot_state_publisher',executable='robot_state_publisher',namespace='rover_1',
             parameters=[{'robot_description':urdf.read_text(),'use_sim_time':True}],
             remappings=[('/tf','/tf'),('/tf_static','/tf_static')],output='screen'),
        watchdog,
        RegisterEventHandler(OnProcessExit(target_action=watchdog,
            on_exit=[EmitEvent(event=Shutdown(reason='Command watchdog exited; simulation must not retain motion'))]))]


def generate_launch_description():
    description=Path(get_package_share_directory('redline_description'))
    return LaunchDescription([DeclareLaunchArgument('world',description='Absolute generated BXW SDF'),
        DeclareLaunchArgument('robot_urdf',default_value=str(description/'urdf/rover_1.urdf')),
        DeclareLaunchArgument('perception_3d',default_value='false'),
        DeclareLaunchArgument('perception_params',default_value=''),
        OpaqueFunction(function=setup),
        Node(package='redline_bringup',executable='ground_filter.py',output='screen',
             condition=IfCondition(LaunchConfiguration('perception_3d')),
             parameters=[LaunchConfiguration('perception_params'),{'use_sim_time':True}])])
