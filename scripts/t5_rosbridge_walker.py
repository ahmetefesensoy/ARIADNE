"""Unreal stand-in for T5: publish an EV1 walk to /crew/EV1/pose over rosbridge.

Uses exactly the rosbridge v2 operations Unreal will send (proje.md §13.2):
``advertise`` then ``publish`` of geometry_msgs/msg/PoseStamped in frame ``map``
at 20 Hz. The path is SIMULATED test motion (straight legs at a fixed speed),
not a plan and not Unreal output. Requires the system python3-websockets.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path

import websockets


def legs_argument(value: str) -> tuple[float, float]:
    heading, _, seconds = value.partition(":")
    return float(heading), float(seconds)


async def walk(args) -> dict:
    report = {"schema": "redline.t5.rosbridge_walker.v1", "status": "SIMULATED",
              "started_utc": datetime.now(timezone.utc).isoformat(), "url": args.url, "topic": args.topic,
              "start_xy_m": args.start, "speed_m_s": args.speed, "legs": args.leg, "rate_hz": args.rate,
              "hold_s": args.hold_s, "return_on_phase": args.return_on_phase, "published": 0, "path": [],
              "events": []}
    phase = {"value": None}
    async with websockets.connect(args.url, open_timeout=10, max_size=32 * 1024 * 1024) as socket:
        await socket.send(json.dumps({"op": "advertise", "topic": args.topic,
                                      "type": "geometry_msgs/msg/PoseStamped"}))
        reader = None
        if args.return_on_phase:
            await socket.send(json.dumps({"op": "subscribe", "id": "walker-phase", "topic": "/redline/mission/state",
                                          "type": "redline_msgs/msg/MissionState", "queue_length": 10}))

            async def read():
                async for frame in socket:
                    data = json.loads(frame)
                    if data.get("op") == "publish" and data.get("topic") == "/redline/mission/state":
                        phase["value"] = data["msg"]["phase"]
            reader = asyncio.create_task(read())
        await asyncio.sleep(1.0)  # let the advertisement reach the ROS graph
        period = 1.0 / args.rate
        points = [tuple(args.start)]
        if args.waypoints:
            points = [tuple(p) for p in json.loads(args.waypoints.read_text(encoding="utf-8"))["waypoints_xy_m"]]
            report["waypoints_file"] = str(args.waypoints)
            report["start_xy_m"] = list(points[0])
        for heading_deg, seconds in args.leg or []:
            ax, ay = points[-1]
            distance = args.speed * seconds
            points.append((ax + distance * math.cos(math.radians(heading_deg)),
                           ay + distance * math.sin(math.radians(heading_deg))))
        state = {"x": points[0][0], "y": points[0][1], "qz": 0.0, "qw": 1.0}

        async def send():
            message = {"header": {"frame_id": "map"},
                       "pose": {"position": {"x": state["x"], "y": state["y"], "z": args.z},
                                "orientation": {"x": 0.0, "y": 0.0, "z": state["qz"], "w": state["qw"]}}}
            await socket.send(json.dumps({"op": "publish", "topic": args.topic, "msg": message}))
            report["published"] += 1
            if report["published"] % args.rate == 0:
                report["path"].append([round(state["x"], 2), round(state["y"], 2)])

        async def follow(route):
            for (ax, ay), (bx, by) in zip(route, route[1:]):
                length = math.hypot(bx - ax, by - ay)
                if length == 0:
                    continue
                heading = math.atan2(by - ay, bx - ax)  # ROS yaw: 0 = east (+x), 90° = north (+y)
                state["qz"], state["qw"] = math.sin(heading / 2), math.cos(heading / 2)
                started, duration = time.monotonic(), length / args.speed
                while True:
                    tick = time.monotonic()
                    fraction = min((tick - started) / duration, 1.0)  # interpolate: no drift off the path
                    state["x"], state["y"] = ax + fraction * (bx - ax), ay + fraction * (by - ay)
                    await send()
                    if fraction >= 1.0:
                        break
                    await asyncio.sleep(max(period - (time.monotonic() - tick), 0.0))

        async def hold(seconds, until=None):
            end = time.monotonic() + seconds
            while time.monotonic() < end and not (until and until()):
                await send()
                await asyncio.sleep(period)

        await follow(points)
        report["events"].append({"event": "outbound_done", "utc": datetime.now(timezone.utc).isoformat()})
        if args.return_on_phase:
            # Wait out on site until the mission orders the return (MissionState RETURN = 4 or later).
            await hold(args.max_wait_s, until=lambda: phase["value"] in (4, 5, 6))
            report["events"].append({"event": "return_ordered", "phase": phase["value"],
                                     "utc": datetime.now(timezone.utc).isoformat()})
            await follow(points[::-1])
            report["events"].append({"event": "home", "utc": datetime.now(timezone.utc).isoformat()})
        if args.hold_s > 0:  # stand still so consumption continues at standing rates
            await hold(args.hold_s)
        await socket.send(json.dumps({"op": "unadvertise", "topic": args.topic}))
        if reader is not None:
            reader.cancel()
    report["end_xy_m"] = [state["x"], state["y"]]
    report["finished_utc"] = datetime.now(timezone.utc).isoformat()
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default="ws://localhost:9090")
    parser.add_argument("--topic", default="/crew/EV1/pose")
    parser.add_argument("--start", type=float, nargs=2, default=(0.0, 0.0), metavar=("X", "Y"))
    parser.add_argument("--waypoints", type=Path, help="JSON with waypoints_xy_m; overrides --start")
    parser.add_argument("--z", type=float, default=0.0, help="presentation z; walkback uses the DEM, not this")
    parser.add_argument("--speed", type=float, default=0.8)
    parser.add_argument("--rate", type=int, default=20)
    parser.add_argument("--leg", type=legs_argument, action="append",
                        help="heading_deg:seconds (ROS yaw, 0 = east); repeat for more legs")
    parser.add_argument("--hold-s", type=float, default=0.0, help="keep publishing the last pose this long")
    parser.add_argument("--return-on-phase", action="store_true",
                        help="after the outbound walk, wait for MissionState RETURN and walk back the same path")
    parser.add_argument("--max-wait-s", type=float, default=600.0)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if not args.leg and not args.waypoints:
        parser.error("give --leg or --waypoints")
    report = asyncio.run(walk(args))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("published", "end_xy_m")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
