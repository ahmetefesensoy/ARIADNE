"""Download only the public visual sources selected for REDLINE on 2026-11-14.

This is asset preparation, independent of the application/ROS/data pipeline.
Original third-party files and their provenance are retained without alteration.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
HEADERS = {"User-Agent": "REDLINE-asset-preparation/1.0", "Referer": "https://github.com/ahmetefesensoy/redline"}
NASA_TERMS = "https://www.nasa.gov/nasa-brand-center/images-and-media/"


def fetch(url: str, path: Path, md5: str | None = None) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with urlopen(Request(url, headers=HEADERS), timeout=120) as response:
            data = response.read()
        if md5 and hashlib.md5(data).hexdigest() != md5:
            raise ValueError(f"Source MD5 mismatch: {path.name}")
        temp = path.with_suffix(path.suffix + ".part")
        temp.write_bytes(data)
        temp.replace(path)
    data = path.read_bytes()
    if md5 and hashlib.md5(data).hexdigest() != md5:
        raise ValueError(f"Cached source MD5 mismatch: {path.name}")
    print(f"{path.relative_to(ROOT)}: {len(data)} bytes", flush=True)
    return {"path": path.relative_to(ROOT).as_posix(), "url": url, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "source_md5": md5}


def nasa(asset_id: str, filename: str, url: str, page: str, credit: str) -> None:
    out = ROOT / "incoming" / asset_id
    record = fetch(url, out / filename)
    if filename.endswith(".glb") and (out / filename).read_bytes()[:4] != b"glTF":
        raise ValueError("Not a GLB")
    (out / "download.json").write_text(json.dumps({"source": page, "credit": credit, "license": "NASA Media Usage Guidelines; third-party/identifier restrictions remain", "license_url": NASA_TERMS, "retrieved_utc": datetime.now(timezone.utc).isoformat(), "files": [record]}, indent=2) + "\n", encoding="utf-8")


def rock(asset_id: str) -> None:
    out = ROOT / "incoming" / asset_id
    out.mkdir(parents=True, exist_ok=True)
    with urlopen(Request(f"https://api.polyhaven.com/info/{asset_id}", headers=HEADERS), timeout=30) as r:
        info = json.load(r)
    with urlopen(Request(f"https://api.polyhaven.com/files/{asset_id}", headers=HEADERS), timeout=30) as r:
        files = json.load(r)
    if info["type"] != 2:
        raise ValueError("Expected a model, not a texture")
    model = files["gltf"]["1k"]["gltf"]
    records = [fetch(model["url"], out / "source.gltf", model["md5"])]
    for rel, entry in model["include"].items():
        path = out / rel
        if not path.resolve().is_relative_to(out.resolve()):
            raise ValueError("Unsafe dependency path")
        records.append(fetch(entry["url"], path, entry["md5"]))
    (out / "download.json").write_text(json.dumps({"source": f"https://polyhaven.com/a/{asset_id}", "credit": info["authors"], "license": "CC0-1.0", "license_url": "https://polyhaven.com/license", "info": info, "retrieved_utc": datetime.now(timezone.utc).isoformat(), "files": records}, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    base = "https://assets.science.nasa.gov/content/dam/science/cds/3d/resources/"
    nasa("pr_1", "source.glb", base + "model/space-exploration-vehicle/Space%20Exploration%20Vehicle.glb", "https://science.nasa.gov/3d-resources/space-exploration-vehicle/", "NASA/LaRC/Advanced Concepts Lab")
    nasa("habitat", "source.glb", base + "model/habitat-demonstration-unit/Habitat%20Demonstration%20Unit%20%28part%201%29.glb", "https://science.nasa.gov/3d-resources/habitat-demonstration-unit/", "NASA/LaRC/Advanced Concepts Lab; part 1")
    nasa("sample_tube", "source.stl", base + "printable/mars-2020-sample-tube/Mars%202020%20sample%20tube.stl", "https://science.nasa.gov/3d-resources/mars-2020-sample-tube/", "NASA/JPL-Caltech; printable sample-tube model")
    nasa("curiosity_reference", "source.blend", "https://raw.githubusercontent.com/nasa/NASA-3D-Resources/master/3D%20Models/Curiosity%20Rover%20(MSL)/Curiosity%20Rover%20(MSL)%20(Clean).blend", "https://github.com/nasa/NASA-3D-Resources/tree/master/3D%20Models/Curiosity%20Rover%20(MSL)", "NASA/JPL-Caltech; NASA-3D-Resources")
    for asset_id in ("rock_07", "rock_09"):
        rock(asset_id)
