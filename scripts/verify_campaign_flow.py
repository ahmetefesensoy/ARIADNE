"""Bounded integration test: SIMULATED human stand-in + actual campaign/science/Nav2.

Run only on a dedicated campaign session before opening an Unreal player.
The pose stand-in teleports between task positions; this does not validate
human traversal, door passage or character animation. Rover poses/commands
are never synthesized by this test. The backend's Nav2 action moves Gazebo.
"""
import argparse
import asyncio
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import time
import yaml
import websockets


async def verify(args):
    args.out.mkdir(parents=True, exist_ok=True)
    targets = yaml.safe_load(args.targets.read_text())
    heights = {t["id"]: t["point_m"][2] for t in targets["targets"]}
    runtime=json.loads((Path(__file__).resolve().parents[1]/"data/engines/BXW/eva-runtime-v1.json").read_text())
    home_z=float(runtime["spawn_map_xyz_m"][2])+1.3
    report = {"schema":"redline.campaign.integration.v1", "created_at_utc":datetime.now(timezone.utc).isoformat(),
        "passed":False,"human_source":"SIMULATED pose stand-in with explicit teleports; no Unreal user",
        "robot_source":"actual ROS/Gazebo odometry and Nav2 action", "science_source":"SIMULATED uncalibrated SCENARIO instruments",
        "scope":"12-step orchestration, product/evidence/custody and actual Nav2 travel; no character/physical instrument acceptance",
        "steps":[],"navigation_statuses":[],"rover_map_positions":[]}
    report['remote_rover_from_lab']=bool(args.remote_rover_from_lab)
    latest = None
    replies = {}
    running = True
    async with websockets.connect(args.url, max_size=5000000) as ws:
        async def send(value): await ws.send(json.dumps(value))
        for topic, typ in (("/redline/campaign/state","std_msgs/msg/String"),
            ("/rover_1/navigate_to_pose/_action/status","action_msgs/msg/GoalStatusArray"),
            ("/redline/science/rover_pose","geometry_msgs/msg/PoseStamped")):
            await send({"op":"subscribe","topic":topic,"type":typ,"throttle_rate":100})
        await send({"op":"advertise","topic":"/crew/EV1/pose","type":"geometry_msgs/msg/PoseStamped"})
        async def receive():
            nonlocal latest
            with (args.out/"ue_feed.jsonl").open("w", encoding="utf-8") as stream:
                async for raw in ws:
                    envelope=json.loads(raw)
                    if envelope.get("op")=="service_response":replies[envelope["id"]]=envelope
                    elif envelope.get("topic")=="/redline/campaign/state":
                        latest=json.loads(envelope["msg"]["data"])
                        stream.write(json.dumps({"elapsed":time.monotonic()-started,"message":envelope},ensure_ascii=False)+"\n")
                    elif envelope.get("topic")=="/redline/science/rover_pose":
                        p=envelope["msg"]["pose"]["position"]
                        report["rover_map_positions"].append([p["x"],p["y"],p["z"]])
                    elif envelope.get("topic")=="/rover_1/navigate_to_pose/_action/status":
                        for entry in envelope["msg"].get("status_list",[]):
                            status=entry["status"]
                            if not report["navigation_statuses"] or report["navigation_statuses"][-1]!=status:
                                report["navigation_statuses"].append(status)
        async def publish():
            while running:
                if latest:
                    t=latest["task"];x,y=t["xy"];z=heights.get(t["target_id"],home_z)
                    if args.remote_rover_from_lab and t['actor']=='rover_1':x,y,z=285.1,-468.,home_z
                    now=time.time();sec=int(now)
                    await send({"op":"publish","topic":"/crew/EV1/pose","msg":{
                        "header":{"frame_id":"map","stamp":{"sec":sec,"nanosec":int((now-sec)*1e9)}},
                        "pose":{"position":{"x":x,"y":y,"z":z},"orientation":{"x":0,"y":0,"z":0,"w":1}}}})
                await asyncio.sleep(.05)
        async def until(predicate, seconds):
            deadline=time.monotonic()+seconds
            while time.monotonic()<deadline:
                if predicate():return
                await asyncio.sleep(.05)
            raise TimeoutError("campaign condition timed out: "+json.dumps(latest,ensure_ascii=False)[:900])
        started=time.monotonic()
        receiver=asyncio.create_task(receive());publisher=asyncio.create_task(publish())
        try:
            await until(lambda:latest is not None,10)
            while not latest["done"]:
                if latest["state"]=="failed":raise RuntimeError(latest["message"])
                task=latest["task"];index=latest["task_index"]
                if task["kind"]=="libs":await until(lambda:latest["rover_connected"],20)
                await asyncio.sleep(1.)  # actual ev_sim receipt and science position
                cmd={"decision":"CHOOSE_RIDGE","assessment":"NEED_MORE_DATA"}.get(task["kind"],"START")
                ident=f"integration-{index}-{latest['revision']}"
                await send({"op":"call_service","id":ident,"service":"/redline/campaign/command",
                    "type":"redline_msgs/srv/MissionCommand","args":{"request_id":ident,"command":cmd,
                        "target_id":task["target_id"],"expected_revision":latest["revision"]}})
                await until(lambda:ident in replies,8)
                reply=replies[ident]
                if not reply.get("result") or not reply.get("values",{}).get("accepted"):
                    raise RuntimeError("command rejected: "+json.dumps(reply,ensure_ascii=False))
                print(json.dumps({"task":task["id"],"accepted":True}),flush=True)
                await until(lambda:latest["task_index"]>index or latest["state"]=="failed",620 if task["kind"]=="scout" else 150)
                if latest["state"]=="failed":raise RuntimeError(latest["message"])
                report["steps"].append({"task":task["id"],"completed_at_wall_s":time.monotonic()-started,
                    "products":list(latest["product_ids"]),"evidence_count":len(latest["evidence_ids"])})
            positions=report["rover_map_positions"]
            displacement=math.dist(positions[0],positions[-1]) if positions else 0
            checks={"twelve_result_gated_steps":len(latest["completed"])==12,
                "persisted_product_count":len(latest["product_ids"])==7,
                "actual_nav2_succeeded":4 in report["navigation_statuses"],
                "rover_moved_over_3m":displacement>3,
                "origin_distinct_from_analysis":latest["samples"][0]["origin_point_m"]!=latest["samples"][0]["analysis_point_m"],
                "field_sample_recorded":latest["samples"][0]["state"]==7,
                "explicit_assessment":latest["decisions"][-1]["chosen"]=="NEED_MORE_DATA"}
            if args.remote_rover_from_lab:
                checks['remote_robot_steps_preserve_field_sites']=all(t['presentation']['interaction_mode']=='remote' and math.dist(t['xy'],(285.1,-468.))>20 for t in latest['tasks'] if t['actor']=='rover_1')
            report.update(checks=checks,passed=all(checks.values()),rover_displacement_m=displacement,final_state=latest)
        except Exception as error:
            report.update(error=str(error),last_state=latest)
        finally:
            running=False;publisher.cancel();receiver.cancel()
            await asyncio.gather(publisher,receiver,return_exceptions=True)
    report["ended_at_utc"]=datetime.now(timezone.utc).isoformat()
    (args.out/"verification.json").write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k not in ("rover_map_positions","final_state","last_state")},ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--url",required=True);p.add_argument("--targets",type=Path,required=True);p.add_argument("--out",type=Path,required=True)
    p.add_argument('--remote-rover-from-lab',action='store_true',help='Dedicated test only: publish explicit simulated EV1 lab pose during remote rover tasks')
    raise SystemExit(asyncio.run(verify(p.parse_args())))
