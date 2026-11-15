"""Read-only rosbridge subscriber: save publish envelopes for UE offline playback.

Requires the system python3-websockets package. Sends subscribe/unsubscribe only;
it never publishes ROS messages, calls services, or sends action goals.
"""

from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

import websockets


def topic_argument(value: str) -> tuple[str, str]:
    topic, separator, message_type = value.partition("=")
    if not separator or not topic.startswith("/") or "/msg/" not in message_type:
        raise argparse.ArgumentTypeError("Expected /topic=package/msg/Type")
    return topic, message_type


async def capture(args: argparse.Namespace) -> dict:
    topics = dict(args.topic or [("/rover_1/odom", "nav_msgs/msg/Odometry")])
    if args.output.resolve() == args.report.resolve():
        raise ValueError("The feed and report must be different files")
    report = {
        "schema": "redline.t4.rosbridge_capture.v1",
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "url": args.url,
        "topics": topics,
        "source": "websocket_subscription; endpoint identity is operator supplied",
        "measurement_status": args.source_status,
        "source_note": args.source_note,
        "sent_operations": [],
        "received_publish_count": 0,
        "topic_counts": {},
        "receipts": [],
        "normalized_multiline_frames": 0,
        "timing_field": "_redline_elapsed_sec; monotonic seconds from first publish",
        "errors": [],
        "passed": False,
    }
    counts: Counter[str] = Counter()
    started = time.monotonic()
    first_publish = None
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    output_opened = False
    try:
        # Exclusive create preserves an existing evidence recording.
        with args.output.open("x", encoding="utf-8", newline="\n") as feed:
            output_opened = True
            async with websockets.connect(
                args.url, open_timeout=args.connect_timeout, max_size=32 * 1024 * 1024
            ) as socket:
                for index, (topic, message_type) in enumerate(topics.items()):
                    request = {
                        "op": "subscribe", "id": f"t4-capture-{index}",
                        "topic": topic, "type": message_type,
                        "throttle_rate": args.throttle_ms, "queue_length": 1,
                    }
                    if topic in ('/tf_static','/redline/bridge/tf_static_snapshot'):
                        request.update(throttle_rate=0,queue_length=100,
                            qos={'history':'keep_last','depth':100,'reliability':'reliable','durability':'transient_local'})
                    await socket.send(json.dumps(request))
                    report["sent_operations"].append(request)
                deadline = time.monotonic() + args.duration
                while (remaining := deadline - time.monotonic()) > 0:
                    try:
                        raw = await asyncio.wait_for(socket.recv(), timeout=remaining)
                    except asyncio.TimeoutError:
                        break
                    if not isinstance(raw, str):
                        report["errors"].append("Unexpected binary frame; requested JSON transport")
                        continue
                    packet = json.loads(raw)
                    if not isinstance(packet, dict):
                        report["errors"].append("Expected a rosbridge JSON object")
                        continue
                    if packet.get("op") != "publish" or packet.get("topic") not in topics:
                        if packet.get("op") == "status" and packet.get("level") == "error":
                            report["errors"].append(packet)
                        continue
                    # Preserve ROS message values and attach playback timing only
                    # to the rosbridge envelope, outside msg.
                    received_at = time.monotonic()
                    if first_publish is None:
                        first_publish = received_at
                    packet["_redline_elapsed_sec"] = received_at - first_publish
                    if "\n" in raw or "\r" in raw:
                        report["normalized_multiline_frames"] += 1
                    feed.write(json.dumps(packet, ensure_ascii=False, separators=(",", ":")) + "\n")
                    feed.flush()
                    counts[packet["topic"]] += 1
                    report["receipts"].append({
                        "index": len(report["receipts"]),
                        "elapsed_sec": received_at - started,
                        "raw_frame_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
                        "topic": packet["topic"],
                        "header": packet.get("msg", {}).get("header"),
                    })
                    if args.max_messages and sum(counts.values()) >= args.max_messages:
                        break
                for index, topic in enumerate(topics):
                    request = {"op": "unsubscribe", "id": f"t4-capture-{index}", "topic": topic}
                    await socket.send(json.dumps(request))
                    report["sent_operations"].append(request)
    except (OSError, ValueError, websockets.WebSocketException) as error:
        report["errors"].append(f"{type(error).__name__}: {error}")
    report["topic_counts"] = dict(counts)
    report["received_publish_count"] = sum(counts.values())
    report["elapsed_sec"] = time.monotonic() - started
    report["missing_topics"] = [topic for topic in topics if counts[topic] < args.min_messages]
    if output_opened:
        payload = args.output.read_bytes()
        report["output"] = str(args.output.resolve())
        report["output_bytes"] = len(payload)
        report["output_sha256"] = hashlib.sha256(payload).hexdigest()
    report["passed"] = not report["errors"] and not report["missing_topics"]
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--url", default="ws://localhost:9090")
    result.add_argument("--topic", action="append", type=topic_argument)
    result.add_argument("--source-status", choices=["ARCHIVE", "DERIVED", "SIMULATED", "SCENARIO"])
    result.add_argument("--source-note", default="Message values preserved; endpoint provenance must be recorded by the operator")
    result.add_argument("--duration", type=float, default=10.0)
    result.add_argument("--connect-timeout", type=float, default=10.0)
    result.add_argument("--throttle-ms", type=int, default=100)
    result.add_argument("--min-messages", type=int, default=2)
    result.add_argument("--max-messages", type=int, default=0)
    result.add_argument("--output", type=Path, required=True)
    result.add_argument("--report", type=Path, required=True)
    return result


def main() -> None:
    argument_parser = parser()
    args = argument_parser.parse_args()
    if args.duration <= 0 or args.connect_timeout <= 0 or args.min_messages < 1:
        argument_parser.error("duration/connect-timeout must be positive; min-messages >= 1")
    if args.throttle_ms < 0 or args.max_messages < 0:
        argument_parser.error("throttle-ms/max-messages must be nonnegative")
    report = asyncio.run(capture(args))
    print(json.dumps({key: report[key] for key in ("passed", "topic_counts", "errors")}))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
