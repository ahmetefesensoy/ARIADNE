"""Real RViz pixels on a private Xvfb display; ROS subscribers and image publisher only.

Run with xvfb-run -a -s '-screen 0 1024x640x24 -nolisten tcp'. Never capture
the user's DISPLAY. This process owns the only application on its X display.
"""
import argparse,hashlib,json,os,signal,subprocess,time,uuid,yaml
from pathlib import Path

def source_fresh(now,clock_at,odom_at,alive):
    return alive and 0<=now-clock_at<2 and 0<=now-odom_at<2

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--seconds',type=float,default=1800)
    a=p.parse_args()
    # xvfb-run provides a private cookie. Forbid the real WSLg screen.
    display=os.environ.get('DISPLAY','')
    if not display.startswith(':') or display in (':0',':0.0') or not os.environ.get('XAUTHORITY'):
        raise RuntimeError('private Xvfb display and authority required; desktop capture forbidden')
    if not 1<=a.seconds<=3600:raise ValueError('bounded stream duration required')
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtCore import QBuffer,QByteArray,QIODevice
    import rclpy
    from sensor_msgs.msg import CompressedImage
    from std_msgs.msg import String
    from nav_msgs.msg import Odometry
    from rosgraph_msgs.msg import Clock
    from rclpy.qos import qos_profile_sensor_data
    from rclpy.qos import QoSProfile,DurabilityPolicy,ReliabilityPolicy
    from tf2_msgs.msg import TFMessage
    a.out.mkdir(parents=True,exist_ok=True)
    app=QApplication([]);screen=app.primaryScreen()
    if screen is None:raise RuntimeError('private capture screen missing')
    env=os.environ.copy();env['QT_QPA_PLATFORM']='xcb';env['GALLIUM_DRIVER']='llvmpipe'
    log=(a.out/'rviz.log').open('w')
    config=yaml.safe_load(a.config.read_text());config['Panels']=[]
    config['Window Geometry'].update({'Width':1024,'Height':640,'X':0,'Y':0,'Hide Left Dock':True,'Hide Right Dock':True})
    config['Visualization Manager']['Global Options']['Frame Rate']=10
    config_path=a.out/'render.rviz';config_path.write_text(yaml.safe_dump(config,sort_keys=False))
    process=subprocess.Popen(['/opt/ros/jazzy/lib/rviz2/rviz2','-d',str(config_path.resolve()),'--ros-args','-p','use_sim_time:=true',
                              '-r','__ns:=/rover_1','-r','__node:=rviz_tablet_render'],env=env,stdout=log,stderr=subprocess.STDOUT)
    rclpy.init();node=rclpy.create_node('rviz_tablet_stream')
    pub=node.create_publisher(CompressedImage,'/redline/rviz/image/compressed',1)
    status=node.create_publisher(String,'/redline/rviz/status',1)
    clock=None;clock_at=-1e20;odom_at=-1e20;previous_odom=None;running=True;has_view_frame=False
    def clk(m):
        nonlocal clock,clock_at,stream_id,count
        if clock is not None and (m.clock.sec,m.clock.nanosec)<(clock.sec,clock.nanosec):
            stream_id=uuid.uuid4().hex;count=0
        if clock!=m.clock:clock=m.clock;clock_at=time.monotonic()
    def odom(m):
        nonlocal odom_at,previous_odom
        stamp=(m.header.stamp.sec,m.header.stamp.nanosec)
        if stamp!=previous_odom:previous_odom=stamp;odom_at=time.monotonic()
    node.create_subscription(Clock,'/clock',clk,qos_profile_sensor_data)
    node.create_subscription(Odometry,'/rover_1/odom',odom,10)
    def static_tf(m):
        nonlocal has_view_frame
        if any(t.header.frame_id=='map' and t.child_frame_id=='redline/navigation_view' for t in m.transforms):has_view_frame=True
    node.create_subscription(TFMessage,'/tf_static',static_tf,QoSProfile(depth=100,durability=DurabilityPolicy.TRANSIENT_LOCAL,reliability=ReliabilityPolicy.RELIABLE))
    def stop(*_):
        nonlocal running
        running=False
    signal.signal(signal.SIGINT,stop);signal.signal(signal.SIGTERM,stop)
    start=time.monotonic();next_frame=start;count=0;stream_id=uuid.uuid4().hex;last=None;first_written=False
    try:
        while running and time.monotonic()-start<a.seconds:
            rclpy.spin_once(node,timeout_sec=.01);app.processEvents();now=time.monotonic()
            if now<next_frame:continue
            next_frame=now+.25
            alive=process.poll() is None
            fresh=source_fresh(now,clock_at,odom_at,alive) and has_view_frame and now-start>3
            # Only this private display's RViz is drawn. No Windows/user desktop.
            image=screen.grabWindow(0).toImage() if alive else None
            data=b''
            if image is not None and not image.isNull():
                if image.width()>1280 or image.height()>800:raise RuntimeError('capture dimensions exceeded bound')
                array=QByteArray();buf=QBuffer(array);buf.open(QIODevice.WriteOnly);image.save(buf,'PNG');data=bytes(array)
            if data and len(data)<=1024*1024 and fresh:
                msg=CompressedImage();msg.header.stamp=clock;msg.header.frame_id='rviz';msg.format='png';msg.data=data
                pub.publish(msg);count+=1
                if not first_written:
                    (a.out/'first-frame.png').write_bytes(data);first_written=True
            else:fresh=False
            info={'schema':'redline.rviz.stream.v1','source':'rviz2/private-xvfb','stream_id':stream_id,'sequence':count,
                  'width':image.width() if image is not None else 0,'height':image.height() if image is not None else 0,
                  'capture_fresh':fresh,'source_fresh':fresh,'physics_fresh':0<=now-clock_at<2,
                  'clock_age_s':min(9999.,max(0.,now-clock_at)),'odom_age_s':min(9999.,max(0.,now-odom_at)),
                  'image_stamp_sec':clock.sec if clock else 0,'image_stamp_nanosec':clock.nanosec if clock else 0,
                  'png_sha256':hashlib.sha256(data).hexdigest() if data else '',
                  'reason':'actual RViz pixels' if fresh else 'RViz/physics/odometry not ready or stale'}
            status.publish(String(data=json.dumps(info)));last=info
            if count%20==0 or not fresh:(a.out/'status.json').write_text(json.dumps(info,indent=2)+'\n')
            if not alive:break
    finally:
        info=last or {'schema':'redline.rviz.stream.v1'};info.update(capture_fresh=False,source_fresh=False,reason='stream stopped')
        status.publish(String(data=json.dumps(info)));rclpy.spin_once(node,timeout_sec=.05)
        node.destroy_node();rclpy.try_shutdown()
        if process.poll() is None:
            process.terminate()
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.wait()
        log.close();(a.out/'verification.json').write_text(json.dumps({'frames':count,'private_display':display,'rviz_exit':process.returncode,
                   'last_status':last,'scope':'Actual RViz render frames; no robot command or synthesized visualization'},indent=2)+'\n')
    return 0 if count else 1
if __name__=='__main__':raise SystemExit(main())
