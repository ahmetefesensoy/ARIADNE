"""Generate ONE 3D asset with the Tripo API (text-to-model). Spends credits only with --go.

Key comes from the TRIPO_API_KEY environment variable; it is never written to disk.
Docs: https://openapi.tripo3d.ai/v3 (quickstart). Output goes to assets/incoming/<asset_id>/
(source.glb + task.json) so SOURCE.md can record the task id, prompt, model and date.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import urllib.error
import urllib.request

BASE_URL = "https://openapi.tripo3d.ai/v3"
DEFAULT_MODEL = "v3.1-20260211"
ROOT = Path(__file__).resolve().parents[1]


def http(method: str, url: str, headers: dict, payload: dict | None = None, timeout: int = 30):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


FAILED = {"failed", "cancelled", "banned", "expired"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("asset_id", help="e.g. astronaut, scout_1")
    ap.add_argument("prompt")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--go", action="store_true", help="actually create the task (spends credits)")
    ap.add_argument("--timeout-s", type=int, default=600)
    args = ap.parse_args()

    out = ROOT / "assets" / "incoming" / args.asset_id
    print(f"asset: {args.asset_id}\nmodel: {args.model}\nprompt: {args.prompt}\noutput: {out}")
    if not args.go:
        print("DRY RUN: nothing sent, no credits spent. Re-run with --go to generate.")
        return 0

    key = os.environ.get("TRIPO_API_KEY")
    if not key:
        print("TRIPO_API_KEY is not set.", file=sys.stderr)
        return 2
    auth = {"Authorization": f"Bearer {key}"}

    status, raw = http("POST", f"{BASE_URL}/generation/text-to-model",
                       {**auth, "Content-Type": "application/json"},
                       {"prompt": args.prompt, "model": args.model})
    body = json.loads(raw)
    if status != 200 or body.get("code") != 0:
        print(f"create failed: HTTP {status} {body}", file=sys.stderr)
        return 1
    task_id = body["data"]["task_id"]
    print(f"task created: {task_id}")

    deadline = time.monotonic() + args.timeout_s
    while time.monotonic() < deadline:
        task = json.loads(http("GET", f"{BASE_URL}/tasks/{task_id}", auth)[1])["data"]
        print(f"status={task['status']} progress={task.get('progress', 0)}%")
        if task["status"] == "success":
            break
        if task["status"] in FAILED:
            print(f"task ended: {task['status']}", file=sys.stderr)
            return 1
        time.sleep(3)
    else:
        print(f"timed out; task {task_id} may still be running", file=sys.stderr)
        return 1

    out.mkdir(parents=True, exist_ok=True)
    code, glb = http("GET", task["output"]["model_url"], {}, timeout=120)
    if code != 200:
        print(f"download failed: HTTP {code}", file=sys.stderr)
        return 1
    (out / "source.glb").write_bytes(glb)
    record = {"task_id": task_id, "model": args.model, "prompt": args.prompt,
              "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "task": {k: v for k, v in task.items() if k != "output"}}
    (out / "task.json").write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"saved {out / 'source.glb'} ({len(glb)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
