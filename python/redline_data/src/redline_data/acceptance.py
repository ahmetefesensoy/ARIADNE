"""T1 data acceptance gates with frozen hashes, not a physical-accuracy claim."""
from __future__ import annotations

from datetime import datetime, timezone
from html import escape
import json
import math
import os
from pathlib import Path
from xml.etree import ElementTree

from .qa import sha256, three_points
from .stac import validate, write


def evaluate_gates(*, qa_fine: dict, qa_plan: dict, vertical: dict,
                   comparison: dict, stac: dict, tests: dict, transfer: dict) -> dict[str, bool]:
    def numeric_qa(qa):
        points = qa.get("three_points", [])
        fraction = qa.get("nodata_fraction", float("nan"))
        return (math.isfinite(fraction) and 0 <= fraction < .02 and len(points) == 3
            and all(math.isfinite(point.get("absolute_error_m", float("nan")))
                    and 0 <= point["absolute_error_m"] <= .1 for point in points))
    products = vertical.get("products", {})
    gale = products.get("MSL_Gale_DEM_Mosaic_1m_v3", {})
    hirise = products.get("DTEEC_019698_1750_019988_1750_U01", {})
    fit = comparison.get("registration", {})
    after = fit.get("after_heldout", {}).get("rmse_m", float("nan"))
    before = fit.get("before_heldout", {}).get("rmse_m", float("nan"))
    bound = fit.get("max_shift_m_per_axis", float("nan"))
    return {
        "fine_source_transfer_and_nodata": numeric_qa(qa_fine),
        "plan_source_transfer_and_nodata": numeric_qa(qa_plan),
        "product_specific_vertical_declarations": (vertical.get("status") == "metadata_verified"
            and gale.get("vertical_datum") == "MOLA" and gale.get("units") == "m"
            and bool(hirise.get("vertical_datum")) and hirise.get("units") == "m"),
        "original_to_ard_numeric_transfer": (transfer.get("passed") is True
            and transfer.get("predeclared_tolerance_m") == .1 and len(transfer.get("points", [])) == 3
            and all(math.isfinite(point.get("abs_residual_m", float("nan")))
                    and 0 <= point["abs_residual_m"] <= .1 for point in transfer.get("points", []))),
        "bounded_relative_registration": (fit.get("converged") is True
            and math.isfinite(bound) and bound > 0
            and all(math.isfinite(fit.get(key, float("nan"))) and abs(fit[key]) < bound
                    for key in ("shift_east_m", "shift_north_m"))
            and math.isfinite(after) and math.isfinite(before) and after >= 0
            and after <= before + max(1e-6, .01*before)
            and fit.get("heldout_cells", 0) >= 10),
        "slope_disagreement_units_and_support": (comparison.get("slope_disagreement", {}).get("unit") == "degree"
            and comparison.get("slope_disagreement", {}).get("baseline_m") == 5
            and "slope_sigma" in comparison.get("assets", {})
            and 0 <= comparison["assets"]["slope_sigma"].get("nodata_fraction", 1) < 1),
        "stac_offline_schema_validation": stac.get("ok") is True
            and stac.get("network_retrieval") is False and stac.get("items_validated", 0) > 0,
        "nonempty_zero_skip_test_run": tests.get("tests", 0) > 0
            and all(tests.get(key) == 0 for key in ("errors", "failures", "skipped")),
    }


def check_t1(*, root: Path, manifest_path: Path, stac_directory: Path,
             schema_root: Path, destination: Path) -> dict:
    root = Path(root).resolve()
    manifest_path, stac_directory, destination = map(Path, (manifest_path, stac_directory, destination))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("site_id") != "BXW":
        raise ValueError("This acceptance profile is specifically for BXW T1")
    # Writer rechecks every data/metadata asset hash and exact catalog JSON.
    written = write("BXW", manifest_path=manifest_path, destination=stac_directory, root=root)
    validated = validate(stac_directory, schema_root=schema_root)
    for name, expected in manifest.get("source_code_sha256", {}).items():
        path = (root/name).resolve()
        if not path.is_relative_to(root) or sha256(path) != expected:
            raise ValueError("Source code/config differs from the tested run snapshot")
    if not manifest.get("source_code_sha256"):
        raise ValueError("Tested source hash snapshot is required")
    report_path = (root/manifest["tests"]["report_path"]).resolve()
    if not report_path.is_relative_to(root) or sha256(report_path) != manifest["tests"]["report_sha256"]:
        raise ValueError("Test report hash differs")
    suites = list(ElementTree.parse(report_path).getroot().iter("testsuite"))
    counts = {key: sum(int(suite.get(key, 0)) for suite in suites) for key in ("tests", "errors", "failures", "skipped")}
    if counts != manifest["tests"]["counts"]:
        raise ValueError("Recorded test counts differ from the actual XML")
    def read(relative):
        path = root/relative
        if relative not in manifest["assets"] or sha256(path) != manifest["assets"][relative]["sha256"]:
            raise ValueError(f"Required acceptance input is not frozen in run manifest: {relative}")
        return json.loads(path.read_text(encoding="utf-8"))
    vertical = read("docs/verification/T1_VERTICAL_DATUM.json")
    transfer = read("docs/verification/T1_HIRISE_TRANSFER.json")
    if (transfer.get("product_id") != "DTEEC_019698_1750_019988_1750_U01"
            or transfer.get("ard_crop", {}).get("sha256") != sha256(root/"data/raw/BXW/hirise_dtm_bxw_019698.tif")
            or transfer.get("helper_sha256") != sha256(root/"scripts/probe_hirise_transfer.py")):
        raise ValueError("Numeric transfer evidence belongs to a different product, crop or helper")
    comparison = read("data/derived/BXW/comparison/comparison.provenance.json")
    qa_fine = read("data/derived/BXW/qa_1m/qa.json")
    qa_plan = read("data/derived/BXW/qa_4m/qa.json")
    # Re-evaluate numerical transfer now; historical QA checkpoint flags are not
    # promoted to a final acceptance claim or used as a physical accuracy test.
    source = root/"data/raw/BXW/gale_dem_v3.tif"
    qa_fine["three_points"] = three_points(source, root/"data/derived/BXW/dem_enu.tif")
    qa_plan["three_points"] = three_points(source, root/"data/derived/BXW/dem_plan_4m.tif")
    gates = evaluate_gates(qa_fine=qa_fine, qa_plan=qa_plan, vertical=vertical,
        comparison=comparison, stac=validated, tests=counts, transfer=transfer)
    result = {"site_id": "BXW", "created_at": datetime.now(timezone.utc).isoformat(),
        "milestone": "T1", "passed": all(gates.values()), "gates": gates,
        "manifest_sha256": sha256(manifest_path), "test_report_sha256": sha256(report_path),
        "tests": counts, "stac": validated, "stac_items": written["items"],
        "vertical_reference": {key: {k: product[k] for k in ("vertical_datum", "units", "realization_status")}
                               for key, product in vertical["products"].items()},
        "registration": comparison["registration"], "slope_disagreement": comparison["slope_disagreement"],
        "three_points_1m": qa_fine["three_points"], "three_points_4m": qa_plan["three_points"],
        "original_to_ard_transfer": {"passed": transfer["passed"],
            "max_abs_residual_m": transfer["max_abs_residual_m"],
            "body_bytes_read": transfer["http"]["body_bytes_read"]},
        "scope": "T1 local data engineering acceptance; no absolute geodetic/physical accuracy or independent one-sigma calibration",
        "remaining_limits": ["MOLA exact areoid realization/version equality not established",
            "DTMs may share source/control; slope_sigma is empirical disagreement in degrees, not independent one-sigma",
            "Registered comparison edges without source support stay unknown; primary DEM nodata gate is separate",
            "SSYS conservative body-envelope convention requires planetary-aware clients",
            "No Unreal/Gazebo terrain, sensor or feature alignment test; these belong to later integration",
            "Horizon/skyview/rocks/environment and engine exports remain separate §6.2 capabilities outside §18 T1 chain"]}
    destination.mkdir(parents=True, exist_ok=True)
    output = destination/"t1_acceptance.json"
    html = destination/"qa_BXW.html"
    if output.exists() or html.exists():
        if not output.is_file() or not html.is_file():
            raise ValueError("Incomplete prior acceptance output; use a new path")
        previous = json.loads(output.read_text(encoding="utf-8"))
        if previous["manifest_sha256"] != result["manifest_sha256"] or previous["stac"]["document_sha256"] != validated["document_sha256"]:
            raise ValueError("Prior acceptance has different inputs")
        if previous.get("html_sha256") != sha256(html):
            raise ValueError("Prior acceptance HTML hash differs")
        return previous
    rows = "".join(f"<tr><td>{escape(name)}</td><td>{'PASS' if passed else 'FAIL'}</td></tr>" for name, passed in gates.items())
    previews = []
    for name, label in (("dem_preview", "DEM"), ("slope_2m_preview", "2 m baseline slope"), ("slope_5m_preview", "5 m baseline slope")):
        record = qa_fine["artifacts"][name]
        relative = os.path.relpath(root/"data/derived/BXW/qa_1m"/record["href"], destination)
        previews.append(f"<figure><img src='{escape(relative)}' width='{record['width']}' height='{record['height']}' alt='{escape(label)}; north up and east right'><figcaption>{escape(label)}: {record['limits']}; {escape(record['encoding'])}; {escape(record['sampling'])}.</figcaption></figure>")
    contents = f"""<!doctype html><html lang="en"><meta charset="utf-8"><title>REDLINE T1 BXW QA</title>
<h1>REDLINE T1 BXW data acceptance</h1><p>{escape(result['created_at'])}. Accepted: {result['passed']}.</p>
<p>3 × 3 km BXW; 1 m terrain and 4 m planning grids. Primary DEM nodata: {qa_fine['nodata_fraction']:.4%}.</p>
<p>This is local data engineering acceptance. Numerical transfer checks do not establish 10 cm physical terrain accuracy.</p>
<table><tr><th>Gate</th><th>Result</th></tr>{rows}</table>
<p>Tests: {counts['tests']}; errors {counts['errors']}; failures {counts['failures']}; skips {counts['skipped']}.</p>
<p>Relative registration: east {comparison['registration']['shift_east_m']:.4f} m, north {comparison['registration']['shift_north_m']:.4f} m.
Heldout RMSE {comparison['registration']['before_heldout']['rmse_m']:.4f} → {comparison['registration']['after_heldout']['rmse_m']:.4f} m. Shared source/control can correlate errors.</p>
<h2>Previews</h2><p>North up, east right; local metre frame. DEM values retain the source MOLA context with scenario H0=0. Slope values are degrees.</p>{''.join(previews)}
<h2>Limits</h2><ul>{''.join('<li>'+escape(value)+'</li>' for value in result['remaining_limits'])}</ul>
<p>Exact hashes, three points, schema versions and provenance are in t1_acceptance.json.</p></html>"""
    with html.open("x", encoding="utf-8") as stream:
        stream.write(contents)
    result["html_sha256"] = sha256(html)
    with output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
    return result
