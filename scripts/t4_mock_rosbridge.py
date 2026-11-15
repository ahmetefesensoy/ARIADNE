"""Bounded synthetic rosbridge server for UE transport tests; no ROS graph.

All generated poses are SIMULATED test values. The optional outage begins after
the first subscription, closes the listener and clients, then opens it again.
Only the /t4/echo service is implemented. This is not an action/control server.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import signal
import time

import websockets


class MockRosbridge:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.started = time.monotonic()
        self.first_subscription = asyncio.Event()
        self.stop = asyncio.Event()
        self.report = {
            "schema": "redline.t4.mock_rosbridge.v1", "status": "SIMULATED",
            "started_utc": datetime.now(timezone.utc).isoformat(),
            "host": args.host, "port": args.port,
            "events": [], "received": [], "sent_publish_count": 0,
            "service_response_count": 0, "published_by_connection": {},
        }
        self.connection_sequence = 0
        self.sequence = 0
        self.clients = set()
        self.first_publish_at = None

    def event(self, kind: str, **details) -> None:
        event = {
            "event": kind, "elapsed_sec": time.monotonic() - self.started, **details,
        }
        self.report["events"].append(event)
        print(json.dumps(event), flush=True)

    def message(self, topic: str) -> dict:
        self.sequence += 1
        stamp = {"sec": self.sequence // 10, "nanosec": (self.sequence % 10) * 100_000_000}
        if topic == "/clock":
            return {"clock": stamp}
        if topic == "/redline/mission/clock":
            # Separate deterministic PET fixture, never substituted for physics.
            return {"clock": {"sec": 3600 + 2 * stamp["sec"], "nanosec": stamp["nanosec"]}}
        if topic in {"/tf", "/tf_static"}:
            return {"transforms": [{
                "header": {"stamp": stamp, "frame_id": "map"},
                "child_frame_id": "rover_1/odom",
                "transform": {
                    "translation": {"x": 0.0, "y": 0.0, "z": 0.0},
                    "rotation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
                },
            }]}
        return {
            "header": {"stamp": stamp, "frame_id": "rover_1/odom"},
            "child_frame_id": "rover_1/base_link",
            "pose": {"pose": {
                "position": {"x": 1.0, "y": 2.0, "z": 3.0},
                "orientation": {"x": 0.0, "y": 0.0, "z": math.sqrt(0.5), "w": math.sqrt(0.5)},
            }, "covariance": [0.0] * 36},
            "twist": {"twist": {
                "linear": {"x": 0.0, "y": 0.0, "z": 0.0},
                "angular": {"x": 0.0, "y": 0.0, "z": 0.0},
            }, "covariance": [0.0] * 36},
        }

    async def handle(self, socket, _path=None) -> None:
        self.clients.add(socket)
        self.connection_sequence += 1
        connection = self.connection_sequence
        self.report["published_by_connection"][str(connection)] = {}
        self.event("connected", connection=connection)
        subscriptions: dict[str, str] = {}

        async def publish() -> None:
            while True:
                for topic, subscription_id in list(subscriptions.items()):
                    publish_at = time.monotonic()
                    if self.first_publish_at is None:
                        self.first_publish_at = publish_at
                    packet = {
                        "op": "publish", "topic": topic, "msg": self.message(topic),
                        "_redline_elapsed_sec": publish_at - self.first_publish_at,
                    }
                    if subscription_id:
                        packet["id"] = subscription_id
                    await socket.send(json.dumps(packet, separators=(",", ":")))
                    self.report["sent_publish_count"] += 1
                    counts = self.report["published_by_connection"][str(connection)]
                    details = counts.setdefault(topic, {
                        "count": 0, "first_elapsed_sec": publish_at - self.started,
                    })
                    details["count"] += 1
                    details["last_elapsed_sec"] = publish_at - self.started
                await asyncio.sleep(self.args.interval)

        publisher = asyncio.create_task(publish())
        try:
            async for raw in socket:
                packet = json.loads(raw)
                self.report["received"].append({
                    "connection": connection, "elapsed_sec": time.monotonic() - self.started,
                    "packet": packet,
                })
                operation = packet.get("op")
                if operation == "subscribe":
                    topic = packet.get("topic", "")
                    if topic in {"/rover_1/odom", "/clock", "/redline/mission/clock", "/tf", "/tf_static"}:
                        subscriptions[topic] = packet.get("id", "")
                        self.first_subscription.set()
                    else:
                        await socket.send(json.dumps({
                            "op": "status", "level": "error", "id": packet.get("id", ""),
                            "msg": "Topic is outside the synthetic T4 fixture",
                        }))
                elif operation == "unsubscribe":
                    subscriptions.pop(packet.get("topic"), None)
                elif operation == "call_service":
                    accepted = packet.get("service") == "/t4/echo"
                    await socket.send(json.dumps({
                        "op": "service_response", "id": packet.get("id", ""),
                        "service": packet.get("service", ""), "result": accepted,
                        "values": {"echo": packet.get("args", {})} if accepted else {},
                    }))
                    self.report["service_response_count"] += 1
                elif operation in {"advertise", "unadvertise", "publish"}:
                    # Recorded only. No forwarding, ROS publisher or actuator exists.
                    pass
                else:
                    await socket.send(json.dumps({
                        "op": "status", "level": "error", "id": packet.get("id", ""),
                        "msg": "Unsupported synthetic test operation",
                    }))
        except websockets.ConnectionClosed:
            pass
        finally:
            publisher.cancel()
            await asyncio.gather(publisher, return_exceptions=True)
            self.clients.discard(socket)
            self.event("disconnected", connection=connection)

    async def close_listener(self, listener) -> None:
        listener.close()
        # Ubuntu's websockets 10.4 awaits asyncio.Server.wait_closed before
        # closing clients. Python 3.12 wait_closed also waits for active clients,
        # so close our tracked clients explicitly to avoid that shutdown cycle.
        await asyncio.gather(
            *(client.close(code=1001, reason="T4 synthetic outage") for client in list(self.clients)),
            return_exceptions=True,
        )
        await listener.wait_closed()

    async def run(self) -> dict:
        listener = None
        try:
            listener = await websockets.serve(self.handle, self.args.host, self.args.port, close_timeout=1)
            # Port=0 is useful for isolated unit/integration tests.
            self.report["port"] = listener.sockets[0].getsockname()[1]
            self.event("listening")
            print(json.dumps({"ready": True, "port": self.report["port"]}), flush=True)

            async def outage() -> None:
                nonlocal listener
                await self.first_subscription.wait()
                await asyncio.sleep(self.args.disconnect_after)
                self.event("outage_begin")
                await self.close_listener(listener)
                listener = None
                await asyncio.sleep(self.args.offline_for)
                listener = await websockets.serve(self.handle, self.args.host, self.report["port"], close_timeout=1)
                self.event("outage_end")

            outage_task = asyncio.create_task(outage()) if self.args.disconnect_after > 0 else None
            try:
                await asyncio.wait_for(self.stop.wait(), timeout=self.args.duration)
            except asyncio.TimeoutError:
                pass
            finally:
                if outage_task:
                    outage_task.cancel()
                    await asyncio.gather(outage_task, return_exceptions=True)
        finally:
            if listener:
                await self.close_listener(listener)
            self.event("stopped")
            self.args.report.parent.mkdir(parents=True, exist_ok=True)
            self.args.report.write_text(json.dumps(self.report, indent=2) + "\n", encoding="utf-8")
        return self.report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9091)
    parser.add_argument("--duration", type=float, default=30.0)
    parser.add_argument("--interval", type=float, default=0.1)
    parser.add_argument("--disconnect-after", type=float, default=0.0)
    parser.add_argument("--offline-for", type=float, default=3.0)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if args.duration <= 0 or args.interval <= 0 or args.offline_for < 0 or args.disconnect_after < 0:
        parser.error("duration/interval must be positive; outage values must be nonnegative")

    async def execute() -> None:
        server = MockRosbridge(args)
        loop = asyncio.get_running_loop()
        for signum in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(signum, server.stop.set)
            except NotImplementedError:
                pass
        await server.run()

    asyncio.run(execute())


if __name__ == "__main__":
    main()
