"""Numerical source→local checks, explicit limits, and reproducible QA previews."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from html import escape
import json
import math
import os
from pathlib import Path

import numpy as np
from pyproj import CRS, Transformer
import rasterio
from rasterio.windows import Window


def sha256(path: Path) -> str:
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def three_points(source_path: Path, local_path: Path, *, tolerance_m: float = .1) -> list[dict]:
    """Compare three separated pixel centres with direct source bilinear samples.

    This checks numerical reprojection, not independent ground truth, DTM
    registration, elevation accuracy or real feature/engine alignment.
    """
    if not math.isfinite(tolerance_m) or tolerance_m <= 0:
        raise ValueError("Tolerance must be finite and positive")
    local_path, source_path = Path(local_path), Path(source_path)
    metadata = json.loads(local_path.with_suffix(".provenance.json").read_text(encoding="utf-8"))
    if metadata.get("sha256") != sha256(local_path) or metadata.get("identity", {}).get("source_sha256") != sha256(source_path):
        raise ValueError("QA input hashes do not match local-frame provenance")
    identity = metadata["identity"]
    if identity["kind"] != "dem":
        raise ValueError("Height QA requires a DEM")
    with rasterio.open(source_path) as source, rasterio.open(local_path) as local:
        crs = CRS.from_wkt(metadata["source_wkt"])
        centre_e, centre_n = Transformer.from_crs(crs.geodetic_crs, crs, always_xy=True).transform(
            identity["center_lon_east"], identity["center_lat"], errcheck=True)
        scale = math.cos(math.radians(identity["center_lat"])) / math.cos(math.radians(identity["expected"]["lat_ts_deg"]))
        results = []
        for fraction_row, fraction_col in ((.2, .25), (.5, .5), (.8, .75)):
            row, col = int(local.height*fraction_row), int(local.width*fraction_col)
            x, y = local.xy(row, col)
            e, n = centre_e + x/scale, centre_n + y
            sc, sr = (~source.transform) * (e, n)
            sc, sr = sc - .5, sr - .5
            c0, r0 = math.floor(sc), math.floor(sr)
            if c0 < 0 or r0 < 0 or c0+1 >= source.width or r0+1 >= source.height:
                raise ValueError("QA control point lacks complete source support")
            neighbours = source.read(1, window=Window(c0, r0, 2, 2), masked=True)
            if np.ma.getmaskarray(neighbours).any() or not np.isfinite(neighbours).all():
                raise ValueError("QA control point has missing source support")
            wr, wc = sr-r0, sc-c0
            reference = float(np.array([1-wr, wr]) @ neighbours.astype("float64") @ np.array([1-wc, wc])) - identity["h0_m"]
            actual = float(local.read(1, window=Window(col, row, 1, 1))[0, 0])
            difference = abs(actual-reference)
            results.append({"row": row, "col": col, "local_xy_m": [x, y],
                "source_EN_m": [e, n], "source_interpolated_height_m": reference,
                "local_height_m": actual, "absolute_error_m": difference,
                "tolerance_m": tolerance_m, "passed": bool(math.isfinite(actual) and difference <= tolerance_m)})
        return results


def _preview(path: Path, output: Path, *, limits: tuple[float, float] | None = None) -> dict:
    """Nearest decimation only; white→black magnitude, magenta missing samples."""
    with rasterio.open(path) as source:
        step = max(1, math.ceil(max(source.height, source.width) / 600))
        # Bound the full read; callers only hand us bounded local products.
        if source.width*source.height > 25_000_000:
            raise ValueError("Preview input exceeds pixel budget")
        values = source.read(1, masked=True).astype("float64").filled(np.nan)[::step, ::step]
        valid = np.isfinite(values)
        if not valid.any():
            raise ValueError("Preview has no valid samples")
        low, high = limits or (float(values[valid].min()), float(values[valid].max()))
        if high < low:
            raise ValueError("Invalid preview limits")
        normalized = np.clip((np.where(valid, values, low)-low) / (high-low if high > low else 1), 0, 1)
        gray = np.round(255*(1-normalized)).astype("uint8")
        rgb = np.stack((gray, gray, gray))
        rgb[:, ~valid] = np.array([255, 0, 255])[:, None]
        with rasterio.open(output, "w", driver="PNG", count=3, height=values.shape[0],
                           width=values.shape[1], dtype="uint8") as image:
            image.write(rgb)
        return {"href": output.name, "sha256": sha256(output), "limits": [low, high],
                "sampling": f"every {step}th source row/column; no smoothing",
                "width": values.shape[1], "height": values.shape[0],
                "encoding": "white=minimum, black=maximum; magenta=missing"}


def report(source: Path, local: Path, *, destination: Path, terrain: Path | None = None) -> dict:
    source, local, destination = Path(source), Path(local), Path(destination)
    points = three_points(source, local)
    metadata = json.loads(local.with_suffix(".provenance.json").read_text(encoding="utf-8"))
    identity = {"source_sha256": sha256(source), "local_sha256": sha256(local),
                "terrain_manifest_sha256": sha256(Path(terrain)/"derivatives.provenance.json") if terrain else None,
                "algorithm": "source-local-qa-v1"}
    report_path = destination / "qa.json"
    if report_path.exists():
        previous = json.loads(report_path.read_text(encoding="utf-8"))
        if previous.get("identity") != identity:
            raise ValueError("Existing QA report has different inputs")
        for artifact in previous["artifacts"].values():
            if sha256(destination/artifact["href"]) != artifact["sha256"]:
                raise ValueError("Existing QA artifact hash differs")
        return previous
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("Incomplete/nonempty QA directory; use a new path")
    with rasterio.open(local) as src:
        if src.width*src.height > 25_000_000:
            raise ValueError("QA input exceeds pixel budget")
        data = src.read(1, masked=True)
        nodata_fraction = float((np.ma.getmaskarray(data) | ~np.isfinite(data.data)).mean())
    destination.mkdir(parents=True, exist_ok=True)
    artifacts = {"dem_preview": _preview(local, destination/"dem_preview.png")}
    histograms = {}
    if terrain:
        terrain = Path(terrain)
        manifest = json.loads((terrain/"derivatives.provenance.json").read_text(encoding="utf-8"))
        if manifest["identity"]["source_sha256"] != identity["local_sha256"]:
            raise ValueError("Terrain products derive from a different local DEM")
        for key in ("slope_2m", "slope_5m"):
            artifact = manifest["assets"][key]
            path = terrain/artifact["href"]
            if sha256(path) != artifact["sha256"]:
                raise ValueError("Terrain product hash differs")
            with rasterio.open(path) as src:
                data = src.read(1, masked=True)
                finite = data.compressed()
                finite = finite[np.isfinite(finite)]
                edges = list(range(0, 91, 5))
                counts, _ = np.histogram(finite, bins=edges)
                histograms[key] = {"edges_degrees": edges, "counts": counts.tolist(),
                    "valid_cells": len(finite), "missing_cells": data.size-len(finite),
                    "intervals": "left-inclusive/right-exclusive; final bin includes 90 degrees"}
            artifacts[key+"_preview"] = _preview(path, destination/f"{key}_preview.png", limits=(0,90))
    numerical_passed = nodata_fraction < .02 and all(point["passed"] for point in points)
    result = {"identity": identity, "created_at": datetime.now(timezone.utc).isoformat(),
        "numerical_checks_passed": numerical_passed, "nodata_fraction": nodata_fraction,
        "three_points": points, "histograms": histograms, "artifacts": artifacts,
        "extent_local_m": [-1500, -1500, 1500, 1500] if metadata["identity"]["size_m"] == [3000,3000] else None,
        "frame_metadata": os.path.relpath(local.with_suffix(".provenance.json"), destination),
        "milestone_T1_complete": False,
        "limitations": ["Three points test numerical source-to-local transfer only; no independent ground truth",
            "Gale source vertical datum unresolved", "No second registered DTM; slope uncertainty unavailable",
            "STAC Collection/Item publication and schema validation pending", "No Unreal/Gazebo/feature alignment test"]}
    paragraphs = ["<!doctype html><html lang='en'><meta charset='utf-8'><title>REDLINE BXW numerical QA</title>",
        "<h1>REDLINE source-to-local numerical QA</h1>",
        f"<p>Created {escape(result['created_at'])}. Numerical checks: {numerical_passed}. T1 complete: false.</p>",
        f"<p>DEM nodata: {nodata_fraction:.4%}. North is up; east is right. Local frame metres.</p>",
        "<p>This checks the implemented coordinate transfer. It does not establish physical terrain accuracy.</p>",
        "<h2>Three separated control points</h2><table><tr><th>row/col</th><th>x/y (m)</th><th>absolute error (m)</th></tr>"]
    for point in points:
        paragraphs.append(f"<tr><td>{point['row']}/{point['col']}</td><td>{point['local_xy_m']}</td><td>{point['absolute_error_m']:.8f}</td></tr>")
    paragraphs.append("</table><h2>Previews</h2>")
    for key, artifact in artifacts.items():
        unit = "degree" if key.startswith("slope") else "source elevation metres; vertical datum unresolved"
        paragraphs.append(f"<figure><img src='{escape(artifact['href'])}' width='{artifact['width']}' height='{artifact['height']}' alt='{escape(key)}: north up, east right; missing samples magenta'><figcaption>{escape(key)}. {unit}. Limits {artifact['limits']}. {escape(artifact['encoding'])}; {escape(artifact['sampling'])}.</figcaption></figure>")
    paragraphs.append("<h2>Slope histograms</h2><p>5 degree bins; raw cell counts (spatially correlated, not independent observations).</p>")
    for key, histogram in histograms.items():
        paragraphs.append(f"<h3>{escape(key)}</h3><table><tr><th>degrees</th><th>cells</th></tr>")
        for low, high, count in zip(histogram["edges_degrees"][:-1], histogram["edges_degrees"][1:], histogram["counts"]):
            paragraphs.append(f"<tr><td>{low}–{high}</td><td>{count}</td></tr>")
        paragraphs.append(f"</table><p>Missing cells: {histogram['missing_cells']}.</p>")
    paragraphs.append("<h2>Open checks</h2><ul>" + "".join(f"<li>{escape(limit)}</li>" for limit in result["limitations"]) + "</ul>")
    paragraphs.append("<p>Methods guidance: Kassis et al. (2026), <a href='https://doi.org/10.48550/arXiv.2609.00065'>Scientific Agent Skills</a>. This is a software/methods attribution, not validation of Mars data.</p></html>")
    html_path = destination/"qa.html"
    html_path.write_text("\n".join(paragraphs), encoding="utf-8")
    result["artifacts"]["html"] = {"href": "qa.html", "sha256": sha256(html_path)}
    report_path.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return result
