"""Space Apps claims ledger: every slide/video claim is checked against its evidence file.

A claim with on_slide=true must pass, or the slide must drop it. A goal (on_slide=false) is reported
under "not_yet" when its evidence does not pass yet; it never blocks and is never shown as done.
Check forms (evidence path relative to the repo root):
  {"key": "a.b.0.c", "equals": v} | {"key": ..., "min": a, "max": b} | {"key": ..., "approx": v, "tol": t}
  {"contains": "text"}            (plain-text evidence)
  {"junit_min_tests": n}          (JUnit XML: at least n tests, zero failures and errors)
Usage: python scripts/space_apps_claims.py [--claims config/space_apps_claims.yaml] [--out ...]
"""
from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_MISSING = object()


def resolve(doc, key: str):
    value = doc
    for part in key.split("."):
        if isinstance(value, dict) and part in value:
            value = value[part]
        elif isinstance(value, list) and part.lstrip("-").isdigit() and -len(value) <= int(part) < len(value):
            value = value[int(part)]
        else:
            return _MISSING
    return value


def _json_check(doc, check: dict) -> dict:
    value = resolve(doc, check["key"])
    out = {"key": check["key"], "observed": None if value is _MISSING else value}
    if value is _MISSING:
        return {**out, "passed": False, "reason": "key not found"}
    if "equals" in check:
        ok = value == check["equals"]
    elif "approx" in check:
        ok = isinstance(value, (int, float)) and abs(value - check["approx"]) <= check.get("tol", 0)
    else:
        ok = isinstance(value, (int, float)) and check.get("min", value) <= value <= check.get("max", value)
    return {**out, "passed": bool(ok)}


def _junit_check(path: Path, minimum: int) -> dict:
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else root.findall("testsuite")
    count = {k: sum(int(s.get(k, 0)) for s in suites) for k in ("tests", "failures", "errors", "skipped")}
    ok = count["tests"] >= minimum and count["failures"] == 0 and count["errors"] == 0
    return {"junit_min_tests": minimum, "observed": count, "passed": ok}


def check_claim(item: dict, root: Path) -> dict:
    path = root / item["evidence"]
    result = {"id": item["id"], "text_en": item["text_en"], "on_slide": bool(item.get("on_slide", True)),
              "evidence": item["evidence"], "checks": []}
    if not path.is_file():
        return {**result, "passed": False, "reason": f"evidence missing: {item['evidence']}"}
    doc = None
    for check in item["checks"]:
        if "contains" in check:
            text = path.read_text(encoding="utf-8")
            result["checks"].append({"contains": check["contains"], "passed": check["contains"] in text})
        elif "junit_min_tests" in check:
            result["checks"].append(_junit_check(path, int(check["junit_min_tests"])))
        else:
            if doc is None:
                doc = json.loads(path.read_text(encoding="utf-8"))
            result["checks"].append(_json_check(doc, check))
    passed = bool(result["checks"]) and all(c["passed"] for c in result["checks"])
    return {**result, "passed": passed, "reason": "" if passed else "a check did not hold"}


def evaluate(items: list[dict], root: Path) -> dict:
    results = [check_claim(item, Path(root)) for item in items]
    return {"schema": "redline.space_apps_claims.v1",
            "slide_ready": all(r["passed"] for r in results if r["on_slide"]),
            "failing_slide_claims": [r["id"] for r in results if r["on_slide"] and not r["passed"]],
            "not_yet": [r["id"] for r in results if not r["on_slide"] and not r["passed"]],
            "claims": results}


def main() -> int:
    import yaml

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--claims", type=Path, default=ROOT / "config/space_apps_claims.yaml")
    parser.add_argument("--out", type=Path, default=ROOT / "docs/verification/SPACE_APPS_CLAIMS.json")
    args = parser.parse_args()
    items = yaml.safe_load(args.claims.read_text(encoding="utf-8"))["claims"]
    report = {**evaluate(items, ROOT), "checked_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "claims_file": str(args.claims.relative_to(ROOT)) if args.claims.is_relative_to(ROOT) else str(args.claims)}
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for r in report["claims"]:
        mark = "PASS" if r["passed"] else ("FAIL" if r["on_slide"] else "NOT YET")
        print(f"{mark:7} {r['id']}: {r['text_en']}")
    print("slide_ready:", report["slide_ready"])
    return 0 if report["slide_ready"] else 1


if __name__ == "__main__":
    sys.exit(main())
