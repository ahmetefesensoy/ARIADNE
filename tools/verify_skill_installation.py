"""Verify the recorded project skills without running their code or accessing a network."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path


def contained(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"Path escapes project: {relative}")
    return path


def content_files(directory: Path) -> dict[str, str]:
    files = {}
    for path in sorted(directory.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        if not path.resolve().is_relative_to(directory.resolve()):
            raise ValueError(f"File escapes skill directory: {path}")
        files[path.relative_to(directory).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return files


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    manifest_path = root / ".agents" / "skills-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    issues = []
    names = set()
    entries = manifest["skills"]
    for entry in entries:
        name = entry["name"]
        if name in names:
            issues.append(f"Duplicate name: {name}")
        names.add(name)
        directory = contained(root, entry["installed_path"])
        text = (directory / "SKILL.md").read_text(encoding="utf-8")
        header = re.match(r"\A---\n(.*?)\n---(?:\n|$)", text, re.DOTALL)
        if not header:
            issues.append(f"{name}: missing frontmatter")
        else:
            declared = re.search(r"^name:\s*['\"]?([a-z0-9-]+)['\"]?\s*$", header[1], re.MULTILINE)
            if not declared or declared[1] != name:
                issues.append(f"{name}: frontmatter name mismatch")
            if not re.search(r"^description:\s*\S", header[1], re.MULTILINE):
                issues.append(f"{name}: missing description")
        expected = entry.get("installed_files_sha256")
        if expected is None:
            issues.append(f"{name}: file manifest not finalized")
            continue
        actual = content_files(directory)
        for path in sorted(expected.keys() - actual.keys()):
            issues.append(f"{name}: missing {path}")
        for path in sorted(actual.keys() - expected.keys()):
            issues.append(f"{name}: unrecorded {path}")
        for path in sorted(expected.keys() & actual.keys()):
            if expected[path] != actual[path]:
                issues.append(f"{name}: changed {path}")
        if entry["source_repository"] and not any(
            path.lower().startswith("license") for path in actual
        ):
            issues.append(f"{name}: no licence file")
    installed = {p.parent.name for p in (root / ".agents" / "skills").glob("*/SKILL.md")}
    for name in sorted(installed - names):
        issues.append(f"Unrecorded skill: {name}")
    print(f"Project skills checked: {len(entries)}")
    print(f"Recorded files checked: {sum(len(e.get('installed_files_sha256', {})) for e in entries)}")
    print(f"Issues: {len(issues)}")
    for issue in issues:
        print(issue)
    return 1 if issues else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Verification failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
