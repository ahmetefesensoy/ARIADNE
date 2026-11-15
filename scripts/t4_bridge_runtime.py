#!/usr/bin/env python3
"""Own rosbridge and the read-only static snapshot adapter as one session."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def main():
    stopped=False
    def stop(_signal,_frame):
        nonlocal stopped
        stopped=True
    signal.signal(signal.SIGINT,stop);signal.signal(signal.SIGTERM,stop)
    processes=[]
    try:
        processes.append(subprocess.Popen([sys.executable,str(Path(__file__).with_name('t4_static_tf_snapshot.py'))],start_new_session=True))
        processes.append(subprocess.Popen(['ros2','launch','rosbridge_server','rosbridge_websocket_launch.xml',
            'address:='+os.environ.get('T4_ROSBRIDGE_ADDRESS','127.0.0.1'),
            'port:='+os.environ.get('T4_ROSBRIDGE_PORT','9090'),
            # UE5.8 native LWS adds a slash to parsed root path. Accept root
            # slash(es) only; retain the same ROS protocol and local binding.
            'url_path:=/+']+sys.argv[1:],start_new_session=True))
        limit=float(os.environ.get('T4_BRIDGE_MAX_SECONDS','600'));deadline=time.monotonic()+limit
        while not stopped and time.monotonic()<deadline and all(p.poll() is None for p in processes):time.sleep(.2)
    finally:
        for process in reversed(processes):
            if process.poll() is None:process.send_signal(signal.SIGINT)
        deadline=time.monotonic()+12
        while time.monotonic()<deadline and any(p.poll() is None for p in processes):time.sleep(.1)
        for process in processes:
            if process.poll() is None:os.killpg(process.pid,signal.SIGKILL)
            process.wait()
    return 0 if all(p.returncode==0 for p in processes) else 1


if __name__=='__main__':raise SystemExit(main())
