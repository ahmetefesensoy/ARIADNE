"""One-time, mechanical research relocation; no application implementation."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import quote, unquote
import os


ROOT = Path(__file__).resolve().parents[1]
IDEAS = (
    "ASTRONOT_ROVER_DRONE.md", "BES_ANA_GOREV_VE_MIMARI.md",
    "GELISTIRME_STRATEJISI.md", "KAYNAK_VE_VARLIK_KATALOGU.md",
    "PROJE_KILAVUZU.md", "PROJE_TANIMI.md", "REDLINE_V3_KILAVUZU.md",
    "REDLINE_V3_UYGULAMA_SPEKI.md", "SKILL_PLANI.md",
    "SPACE_APPS_ARASTIRMA.md", "SPACE_APPS_KAPSAMLI_ARASTIRMA.md",
    "TASARIM_GOZDEN_GECIRME.md",
)
MOVES = {name: f"research/proje-fikirleri/{name}" for name in IDEAS}
MOVES.update({
    "YENI_DEPO_AKTARIMI.md": "research/handoff/YENI_DEPO_AKTARIMI.md",
    "HANDOFF_MANIFEST.json": "research/handoff/HANDOFF_MANIFEST.json",
    "research/FILE_TIMESTAMPS.json": "research/history/2026-11-14-first-publication-files.json",
    "research/PUBLICATION_CHECKS.md": "research/history/2026-11-14-first-publication-checks.md",
})


def main() -> None:
    mapping = {(ROOT / old).resolve(): (ROOT / new).resolve() for old, new in MOVES.items()}
    candidates = list(ROOT.glob("*.md"))
    for folder in ("docs", "research-notes", "research"):
        candidates.extend((ROOT / folder).rglob("*.md"))
    candidates.append(ROOT / ".agents/skills/redline-space-apps/SKILL.md")
    originals = {p: p.read_text(encoding="utf-8") for p in candidates if p.is_file()}
    for old, new in MOVES.items():
        source, target = ROOT / old, ROOT / new
        if not source.is_file() or target.exists():
            raise RuntimeError(f"Unexpected relocation state: {old} -> {new}")
        target.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "mv", "--", old, new], cwd=ROOT, check=True)
    changed = []
    for old_path, text in originals.items():
        new_path = mapping.get(old_path.resolve(), old_path)

        def replace(match: re.Match[str]) -> str:
            target = match[2]
            if target.startswith(("http:", "https:", "mailto:", "#")) or " " in target:
                return match[0]
            file_part, sep, fragment = target.partition("#")
            resolved = (old_path.parent / unquote(file_part)).resolve()
            if resolved == ROOT / "önceki deneme" or ROOT / "önceki deneme" in resolved.parents:
                return match[1] + " (bu depoya dahil edilmedi)"
            replacement = mapping.get(resolved, resolved)
            if new_path == old_path and replacement == resolved:
                return match[0]
            relative = Path(os.path.relpath(replacement, new_path.parent)).as_posix()
            return "[" + match[1] + "](" + quote(relative, safe="/._-") + (sep + fragment if sep else "") + ")"

        updated = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", replace, text)
        if updated != text:
            new_path.write_text(updated, encoding="utf-8", newline="\n")
            changed.append(new_path.relative_to(ROOT).as_posix())
    manifest_path = ROOT / ".agents/skills-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entry = next(e for e in manifest["skills"] if e["name"] == "redline-space-apps")
    skill = ROOT / entry["installed_path"] / "SKILL.md"
    entry["installed_files_sha256"]["SKILL.md"] = hashlib.sha256(skill.read_bytes()).hexdigest()
    manifest.setdefault("notes", []).append(
        "2026-11-14: local redline-space-apps links relocated with project idea documents; upstream skills unchanged."
    )
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"moved": len(MOVES), "links_updated_in": changed}, ensure_ascii=False))


if __name__ == "__main__":
    main()
