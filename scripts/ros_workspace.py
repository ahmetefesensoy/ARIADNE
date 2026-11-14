"""Build an exact ROS source snapshot in an ASCII Linux cache directory.

Some rosidl/CMake generators do not preserve a Windows-mounted source path
containing spaces and Turkish characters. Each invocation gets a fresh workspace
whose name includes the full source-tree content hash; no old overlay is reused.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import tempfile


def file_records(directory: Path) -> list[dict[str, str | int]]:
    records = []
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"ROS source snapshot rejects symlinks: {path}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise ValueError(f"ROS source is not a regular file: {path}")
        data = path.read_bytes()
        records.append(
            {
                "path": path.relative_to(directory).as_posix(),
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    if not records:
        raise ValueError(f"ROS source directory is empty: {directory}")
    return records


def prepare(source: Path, cache: Path, provenance: Path) -> None:
    source = source.resolve(strict=True)
    cache = cache.resolve()
    if str(cache).startswith("/mnt/") or cache.is_relative_to(source):
        raise ValueError("ROS build cache must be outside source on a Linux filesystem")
    try:
        str(cache).encode("ascii")
    except UnicodeEncodeError as error:
        raise ValueError("Set REDLINE_ROS_CACHE to an ASCII Linux cache path") from error
    if " " in str(cache):
        raise ValueError("Set REDLINE_ROS_CACHE to a Linux cache path without spaces")
    records = file_records(source)
    fingerprint = hashlib.sha256(
        json.dumps(records, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    cache.mkdir(parents=True, exist_ok=True)
    workspace = Path(tempfile.mkdtemp(prefix=f"ws-{fingerprint[:16]}-", dir=cache))
    snapshot = workspace / "src"
    shutil.copytree(source, snapshot)
    if file_records(snapshot) != records or file_records(source) != records:
        raise ValueError("ROS source changed during snapshot or copied hashes differ")
    record = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": str(source),
        "workspace": str(workspace),
        "source_tree_sha256": fingerprint,
        "source_snapshot_verified": True,
        "fresh_workspace": True,
        "files": records,
    }
    (workspace / "source-manifest.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    provenance.parent.mkdir(parents=True, exist_ok=True)
    provenance.write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(workspace)


def collect(workspace: Path, destination: Path) -> None:
    """Copy only this run's reports; do not serve reports from an older run."""
    for path in (workspace / "build").glob("**/test_results/**/*.xml"):
        target = destination / "ros" / path.relative_to(workspace)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    if (workspace / "log").is_dir():
        shutil.copytree(workspace / "log", destination / "ros" / "log")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_parser = commands.add_parser("prepare")
    prepare_parser.add_argument("source", type=Path)
    prepare_parser.add_argument("cache", type=Path)
    prepare_parser.add_argument("provenance", type=Path)
    collect_parser = commands.add_parser("collect")
    collect_parser.add_argument("workspace", type=Path)
    collect_parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.source, args.cache, args.provenance)
    else:
        collect(args.workspace, args.destination)


if __name__ == "__main__":
    main()
