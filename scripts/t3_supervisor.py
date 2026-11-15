"""Isolated process-group owner for a bounded REDLINE simulation experiment."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time


def main():
    signal.signal(signal.SIGINT, signal.default_int_handler)
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--workspace',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path);parser.add_argument('--smoke',action='store_true')
    parser.add_argument('--rviz',action='store_true')
    parser.add_argument('--rviz-config',type=Path,help='Optional diagnostic RViz view, owned by this supervisor')
    parser.add_argument('--rviz-driver',choices=['llvmpipe','d3d12'],default='llvmpipe',help='Explicit WSL RViz renderer; d3d12 requires a verified working GPU adapter')
    parser.add_argument('--navigation-view',action='store_true',help='Display-only planar map/path copies at Mars elevation')
    parser.add_argument('--gazebo-gui',action='store_true')
    parser.add_argument('--scout-model',type=Path,help='Optional original SCENARIO scout model, sharing this single physics world')
    parser.add_argument('--terrain',type=Path,help='Optional verified surface manifest')
    parser.add_argument('--delivered-rover',action='store_true',help='Stage the delivered NASA-derived metre-scale rover on the six-wheel fallback')
    parser.add_argument('--obstacle-fixture',action='store_true',help='SCENARIO tall LiDAR acceptance target, 5 m ahead')
    parser.add_argument('--rviz-goal',action='store_true',help='Observe a real RViz goal instead of sending a programmatic goal')
    parser.add_argument('--rotation-probe',action='store_true',help='Simulation-only bounded turn; no Nav2 command owner')
    parser.add_argument('--controller',choices=['mppi','rpp'],default='mppi',help='Explicit delivered-rover controller comparison')
    parser.add_argument('--lidar-3d',action='store_true',help='Optional measured-only ground/obstacle segmentation commissioning')
    parser.add_argument('--perception-probe',action='store_true',help='Stationary low-fixture detection probe, no Nav2')
    parser.add_argument('--obstacle-height',type=float,default=3.5)
    parser.add_argument('--stationary-hold',type=float,default=0,help='Read-only full navigation graph hold, no goal (seconds)')
    args=parser.parse_args()
    if args.controller!='mppi' and not args.delivered_rover:parser.error('controller comparison requires --delivered-rover')
    if args.lidar_3d and not args.delivered_rover:parser.error('3D sensing commissioning requires --delivered-rover')
    if args.perception_probe and not (args.lidar_3d and args.obstacle_fixture):parser.error('perception probe requires 3D LiDAR and a fixture')
    if args.stationary_hold and not 1<=args.stationary_hold<=3600:parser.error('stationary hold must be in [1,3600] seconds')
    if args.rviz_config and not args.rviz_config.is_file():parser.error('RViz config does not exist')
    if args.navigation_view and args.rviz_goal:
        parser.error('navigation-view uses a display frame; the map-frame RViz acceptance observer is not enabled for it')
    root=Path(__file__).resolve().parent.parent;out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    ws=args.workspace.resolve();cache=Path.home()/'.cache/redline/t3/terrain-bxw-v2'
    terrain=args.terrain.resolve() if args.terrain else cache/'manifest.json'
    cache=terrain.parent
    if not args.smoke and not terrain.is_file():raise ValueError('Run terrain export before T3 runtime')
    description=ws/'install/redline_description/share/redline_description/models/rover_1/model.sdf'
    urdf=ws/'install/redline_description/share/redline_description/urdf/rover_1.urdf'
    geometry=json.loads((ws/'install/redline_description/share/redline_description/geometry.json').read_text())
    nav_params=None
    if args.delivered_rover:
        rover_cache=Path.home()/'.cache/redline/t3/rovers';rover_cache.mkdir(parents=True,exist_ok=True)
        rover_dir=Path(tempfile.mkdtemp(prefix='delivered-',dir=rover_cache))/'model'
        stage_command=[sys.executable,str(ws/'src/redline_description/scripts/stage_delivered_rover.py'),
                        '--asset',str(root/'assets/incoming/rover_1/asset.json'),'--out',str(rover_dir),
                        '--nav-config',str(ws/'install/redline_navigation/share/redline_navigation/config/nav2.yaml'),
                        '--controller',args.controller]
        if args.lidar_3d:stage_command+=['--lidar-3d']
        subprocess.run(stage_command,check=True,timeout=30,
                       stdout=(out/'rover-stage.log').open('w'))
        description=rover_dir/'model.sdf';urdf=rover_dir/'rover_1.urdf'
        geometry=json.loads((rover_dir/'geometry.json').read_text())
        (out/'rover-geometry.json').write_text(json.dumps(geometry,indent=2)+'\n')
        nav_params=rover_dir/'nav2.yaml'
        (out/'nav2-delivered.yaml').write_bytes(nav_params.read_bytes())
    clearance=geometry['root_ground_clearance_m']
    world=out/'bxw.sdf'
    command=['ros2','run','redline_gazebo','prepare_world.py','--rover',str(description),'--out',str(world),
             '--root-clearance',str(clearance)]
    if args.smoke:command+=['--smoke']
    else:command+=['--terrain',str(terrain)]
    if args.obstacle_fixture:command+=['--obstacle-fixture','--obstacle-height',str(args.obstacle_height)]
    subprocess.run(command,check=True,timeout=20)
    if args.scout_model:
        import xml.etree.ElementTree as ET
        source=ET.parse(args.scout_model).getroot().find('model')
        if source is None or source.get('name')!='scout_1':raise ValueError('Expected one scout_1 SDF model')
        document=ET.parse(world);document.getroot().find('world').append(source)
        document.write(world,encoding='utf-8',xml_declaration=True)
    subprocess.run(['gz','sdf','-k',str(world)],check=True,timeout=20,stdout=(out/'sdf-check.log').open('w'),stderr=subprocess.STDOUT)
    processes=[];files=[]
    def launch(name,cmd):
        logfile=(out/(name+'.log')).open('w');files.append(logfile)
        process=subprocess.Popen(cmd,stdout=logfile,stderr=subprocess.STDOUT,start_new_session=True)
        processes.append((name,process));return process
    start_wall=time.time()
    result={'started_at_utc':datetime.now(timezone.utc).isoformat(),'workspace':str(ws),'world':str(world),
            'world_sha256':hashlib.sha256(world.read_bytes()).hexdigest(),'physics':'Gazebo Harmonic','passed':False,'smoke':args.smoke,
            'rover_profile':'delivered visual / six-wheel fallback; see staged geometry for physics' if args.delivered_rover else 'primitive fixture',
            'root_clearance_m':clearance,
            'obstacle_fixture':args.obstacle_fixture,
            'controller_profile':args.controller,
            'lidar_3d':args.lidar_3d,
            'obstacle_height_m':args.obstacle_height,
            'robot_sdf':str(description),'robot_urdf':str(urdf),
            'runtime_scripts_sha256':{name:hashlib.sha256((root/'scripts'/name).read_bytes()).hexdigest()
                for name in ('t3_supervisor.py','capture_t3_motion.py','inspect_t3_perception.sh','probe_t3_rotation.py','probe_t3_perception.py')},
            'core_inputs':json.loads((ws/'t3-core-inputs.json').read_text()) if (ws/'t3-core-inputs.json').exists() else [],
            'render_environment':{key:os.environ.get(key) for key in ('GALLIUM_DRIVER','MESA_D3D12_DEFAULT_ADAPTER_NAME','DISPLAY')}}
    # Non-interactive background shells may pass SIGINT as ignored. Own these
    # signals explicitly so the outer campaign owner can reach this cleanup.
    def request_stop(signum, _frame):
        raise RuntimeError(f'Supervisor stopped by signal {signum}')
    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    try:
        simulation_command=['ros2','launch','redline_bringup','simulation.launch.py','world:='+str(world),'robot_urdf:='+str(urdf)]
        if args.lidar_3d:simulation_command+=['perception_3d:=true','perception_params:='+str(rover_dir/'perception.json')]
        sim=launch('simulation',simulation_command)
        if args.gazebo_gui:launch('gazebo_gui',['gz','sim','-g','-v','3',str(world)])
        if args.perception_probe:
            probe=launch('perception_probe',[sys.executable,str(root/'scripts/probe_t3_perception.py'),
                                            '--out',str(out/'perception-result.json')])
            probe.wait(timeout=65)
            result['perception']=json.loads((out/'perception-result.json').read_text())
            result['passed']=probe.returncode==0 and result['perception']['passed']
        elif args.rotation_probe:
            probe=launch('rotation_probe',[sys.executable,str(root/'scripts/probe_t3_rotation.py'),
                                          '--out',str(out/'rotation-result.json')])
            probe.wait(timeout=80)
            result['rotation']=json.loads((out/'rotation-result.json').read_text())
            result['passed']=probe.returncode==0 and result['rotation']['passed']
        elif args.smoke:
            # Only sensor and wheel-odometry transport, no navigation acceptance.
            time.sleep(10)
            probe=launch('smoke_topics',['ros2','topic','list'])
            probe.wait(timeout=10)
            topics=(out/'smoke_topics.log').read_text()
            result['topics']=topics.splitlines()
            # Actual typed ROS subscriber receives live data rather than treating
            # topic advertisement as a sensor success.
            from sensor_msgs.msg import Image,Imu,LaserScan
            from nav_msgs.msg import Odometry
            import rclpy
            from rclpy.qos import qos_profile_sensor_data
            rclpy.init();node=rclpy.create_node('t3_sensor_probe');counts={}
            subs=[]
            for topic,kind in [('/rover_1/scan',LaserScan),('/rover_1/imu',Imu),('/rover_1/camera/image',Image),('/rover_1/depth/image',Image),('/rover_1/odom_raw',Odometry)]:
                counts[topic]=0
                def receive(message,key=topic):counts[key]+=1
                subs.append(node.create_subscription(kind,topic,receive,qos_profile_sensor_data))
            end=time.monotonic()+25
            while time.monotonic()<end and min(counts.values())<2:rclpy.spin_once(node,timeout_sec=.1)
            result['sensor_counts']=counts;result['passed']=min(counts.values())>=2
            node.destroy_node();rclpy.try_shutdown()
        else:
            value=json.loads(terrain.read_text());spawn=value['spawn'];goal=value['goal']
            result['terrain_sha256']=hashlib.sha256(terrain.read_bytes()).hexdigest()
            nav_command=['ros2','launch','redline_navigation','navigation.launch.py',
                'map:='+str(cache/value['nav']['yaml']),'spawn_x:='+str(spawn['map_x_m']),
                'spawn_y:='+str(spawn['map_y_m']),'spawn_z:='+str(spawn['ground_z_m']+clearance),'spawn_yaw:='+str(spawn['yaw_rad']),
                'rviz:='+str((args.rviz or args.rviz_goal) and not args.rviz_config).lower()]
            if nav_params:nav_command+=['params_file:='+str(nav_params)]
            nav=launch('navigation',nav_command)
            if args.navigation_view:
                launch('navigation_view',[sys.executable,str(root/'scripts/rviz_navigation_view.py'),
                                          '--height',str(spawn['ground_z_m']),'--ros-args','-p','use_sim_time:=true'])
            if args.rviz_config:
                launch('rviz',['env','GALLIUM_DRIVER='+args.rviz_driver,'ros2','run','rviz2','rviz2',
                              '-d',str(args.rviz_config.resolve()),'--ros-args','-p','use_sim_time:=true',
                              '-r','__ns:=/rover_1','-r','__node:=rviz_navigation'])
            launch('physical_motion',[sys.executable,str(root/'scripts/capture_t3_motion.py'),
                                      '--runtime',str(out),'--terrain',str(terrain)])
            # Read-only probe starts with navigation; it waits for data and owns
            # no goal or velocity publishers. Preserve empty observations too.
            launch('perception',['bash',str(root/'scripts/inspect_t3_perception.sh'),'--duration','40'])
            verify_command=['ros2','run','redline_bringup','verify_navigation.py',
                 '--terrain',str(terrain),'--out',str(out/'navigation_result.json'),'--timeout','180','--root-clearance',str(clearance)]
            if args.stationary_hold:
                verify_command=[sys.executable,str(root/'scripts/hold_t3_navigation.py'),'--workspace',str(ws),
                                '--out',str(out/'navigation_result.json'),'--seconds',str(args.stationary_hold)]
            observer=None
            if args.rviz_goal:
                # Own the actual observer PID so SIGINT reaches rclcpp directly.
                # The ros2 run wrapper can remain alive until the kill deadline.
                observer_binary=ws/'install/redline_bringup/lib/redline_bringup/rviz_goal_observer'
                observer=launch('rviz_goal_observer',[str(observer_binary)])
                verify_command+=['--rviz-goal','--goal-wait-timeout','300']
            verifier=launch('verification',verify_command)
            deadline=time.monotonic()+(args.stationary_hold+100 if args.stationary_hold else 600 if args.rviz_goal else 300)
            while time.monotonic()<deadline and verifier.poll() is None:
                if sim.poll() is not None or nav.poll() is not None:raise RuntimeError('Simulation/navigation process exited early')
                if observer is not None and observer.poll() is not None:raise RuntimeError('RViz goal observer exited early')
                time.sleep(.25)
            if verifier.poll() is None:raise RuntimeError('Bounded navigation verifier timeout')
            if verifier.returncode!=0:raise RuntimeError('Navigation verifier failed; inspect logs')
            check=json.loads((out/'navigation_result.json').read_text());result['navigation']=check;result['passed']=check['passed']
    except Exception as error:
        result['error']=str(error)
    finally:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        for _name,process in reversed(processes):
            if process.poll() is None:
                # ros2 launch forwards SIGINT to its children. Signalling the
                # entire group here would deliver it twice to every child.
                try:process.send_signal(signal.SIGINT)
                except ProcessLookupError:pass
        deadline=time.monotonic()+12
        while time.monotonic()<deadline and any(p.poll() is None for _,p in processes):time.sleep(.1)
        for _name,process in processes:
            if process.poll() is None:
                try:os.killpg(process.pid,signal.SIGKILL)
                except ProcessLookupError:pass
            process.wait()
        for logfile in files:logfile.close()
        renderer_log=Path.home()/'.gz/rendering/ogre2.log'
        if renderer_log.is_file() and renderer_log.stat().st_mtime>=start_wall:
            lines=renderer_log.read_text(errors='replace').splitlines()
            result['render_device_lines']=[line for line in lines if 'GL_RENDERER =' in line or 'GL_VENDOR =' in line]
        result['processes']={name:process.returncode for name,process in processes}
        child_errors=[]
        for name,_process in processes:
            path=out/(name+'.log')
            if path.is_file():
                child_errors.extend({'log':path.name,'line':line} for line in path.read_text(errors='replace').splitlines()
                                    if 'process has died' in line or 'failed to terminate' in line)
        result['clean_shutdown']=not child_errors and all(process.returncode==0 for _,process in processes)
        result['child_exit_diagnostics']=child_errors
        result['pass_scope']='Requested sensor/motion/navigation phase only; clean_shutdown is separate'
        if args.stationary_hold:result['pass_scope']='Read-only stationary integration hold; no navigation/motion goal was sent'
        result['ended_at_utc']=datetime.now(timezone.utc).isoformat()
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='navigation'},indent=2))
    return 0 if result['passed'] else 1

if __name__=='__main__':sys.exit(main())
