"""Transport evidence tests use loopback websocket fixtures, never a ROS graph."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import websockets


def load_script(name: str):
    path = Path(__file__).resolve().parents[1] / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


capture_module = load_script("t4_capture_feed")
mock_module = load_script("t4_mock_rosbridge")


class TransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_capture_preserves_messages_timing_and_only_subscribes(self):
        received = []
        originals = [
            {"op": "publish", "topic": "/rover_1/odom", "msg": {"pose": {"x": 0.125}, "label": "SIMULATED"}},
            {"op": "publish", "topic": "/rover_1/odom", "msg": {"pose": {"x": 0.25}, "label": "SIMULATED"}},
        ]

        async def handle(socket, _path=None):
            received.append(json.loads(await socket.recv()))
            for packet in originals:
                await socket.send(json.dumps(packet))
                await asyncio.sleep(0.02)
            received.append(json.loads(await socket.recv()))

        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            async with websockets.serve(handle, "127.0.0.1", 0) as server:
                port = server.sockets[0].getsockname()[1]
                args = capture_module.parser().parse_args([
                    "--url", f"ws://127.0.0.1:{port}", "--duration", "1",
                    "--max-messages", "2", "--output", str(target / "feed.jsonl"),
                    "--report", str(target / "report.json"),
                ])
                report = await capture_module.capture(args)
            self.assertTrue(report["passed"], report)
            lines = [json.loads(line) for line in args.output.read_text().splitlines()]
            self.assertEqual([line["msg"] for line in lines], [packet["msg"] for packet in originals])
            self.assertEqual(lines[0]["_redline_elapsed_sec"], 0.0)
            self.assertGreater(lines[1]["_redline_elapsed_sec"], lines[0]["_redline_elapsed_sec"])
            self.assertEqual([packet["op"] for packet in received], ["subscribe", "unsubscribe"])
            self.assertEqual(report["output_sha256"], hashlib.sha256(args.output.read_bytes()).hexdigest())
            # Existing evidence must remain intact and a failed capture is reported.
            prior = args.output.read_bytes()
            failed_report = await capture_module.capture(args)
            self.assertFalse(failed_report["passed"])
            self.assertEqual(args.output.read_bytes(), prior)

    async def test_mock_closes_listener_and_requires_resubscription_after_reconnect(self):
        with tempfile.TemporaryDirectory() as directory:
            server = mock_module.MockRosbridge(argparse.Namespace(
                host="127.0.0.1", port=0, duration=3, interval=0.01,
                disconnect_after=0.15, offline_for=0.25,
                report=Path(directory) / "mock.json",
            ))
            task = asyncio.create_task(server.run())
            try:
                await self.wait_event(server, "listening")
                url = f"ws://127.0.0.1:{server.report['port']}"
                async with websockets.connect(url) as socket:
                    await socket.send(json.dumps({"op": "subscribe", "topic": "/rover_1/odom", "id": "before"}))
                    first = json.loads(await asyncio.wait_for(socket.recv(), 1))
                    self.assertEqual(first["msg"]["header"]["frame_id"], "rover_1/odom")
                    self.assertEqual(first["msg"]["pose"]["pose"]["position"], {"x": 1.0, "y": 2.0, "z": 3.0})
                    await asyncio.wait_for(socket.wait_closed(), 1)
                await self.wait_event(server, "outage_begin")
                with self.assertRaises(OSError):
                    async with websockets.connect(url, open_timeout=0.1):
                        pass
                await self.wait_event(server, "outage_end")
                async with websockets.connect(url) as socket:
                    # A fresh connection does not inherit stale subscriptions.
                    with self.assertRaises(asyncio.TimeoutError):
                        await asyncio.wait_for(socket.recv(), 0.03)
                    await socket.send(json.dumps({"op": "subscribe", "topic": "/tf_static", "id": "after"}))
                    message = json.loads(await asyncio.wait_for(socket.recv(), 1))
                    self.assertEqual(message["id"], "after")
                    transform = message["msg"]["transforms"][0]
                    self.assertEqual(transform["header"]["frame_id"], "map")
                    self.assertEqual(transform["child_frame_id"], "rover_1/odom")
                    await socket.send(json.dumps({"op": "call_service", "service": "/t4/echo", "id": "service-2", "args": {"value": 3}}))
                    while True:
                        response = json.loads(await asyncio.wait_for(socket.recv(), 1))
                        if response["op"] == "service_response":
                            break
                    self.assertTrue(response["result"])
                    self.assertEqual(response["id"], "service-2")
                    self.assertEqual(response["values"], {"echo": {"value": 3}})
            finally:
                server.stop.set()
                report = await task
            self.assertEqual(report["status"], "SIMULATED")
            self.assertEqual(report["service_response_count"], 1)
            self.assertEqual(len([event for event in report["events"] if event["event"] == "connected"]), 2)

    async def wait_event(self, server, kind):
        async def wait():
            while not any(event["event"] == kind for event in server.report["events"]):
                await asyncio.sleep(0.005)
        await asyncio.wait_for(wait(), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
