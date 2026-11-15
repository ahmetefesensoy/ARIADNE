"""Record small portable metadata/hashes; this is NOT a STAC Collection writer."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
from xml.etree import ElementTree


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", required=True)
    parser.add_argument("--test-report", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--include-comparison", action="store_true")
    args = parser.parse_args()
    if not args.site.isascii() or not args.site.replace("_", "").isalnum():
        parser.error("Expected a simple site identifier")
    root = Path(__file__).resolve().parent.parent
    relative_paths = [f"data/raw/{args.site}/gale_dem_v3.tif",
        f"data/derived/{args.site}/dem_enu.tif", f"data/derived/{args.site}/dem_plan_4m.tif",
        f"data/derived/{args.site}/terrain/slope_2m.tif", f"data/derived/{args.site}/terrain/slope_5m.tif",
        f"data/derived/{args.site}/terrain/roughness.tif",
        f"data/derived/{args.site}/qa_1m/qa.json", f"data/derived/{args.site}/qa_1m/qa.html",
        f"data/derived/{args.site}/qa_1m/dem_preview.png",
        f"data/derived/{args.site}/qa_1m/slope_2m_preview.png",
        f"data/derived/{args.site}/qa_1m/slope_5m_preview.png"]
    metadata_paths = [f"data/raw/{args.site}/gale_dem_v3.provenance.json",
        f"data/derived/{args.site}/dem_enu.provenance.json", f"data/derived/{args.site}/dem_plan_4m.provenance.json",
        f"data/derived/{args.site}/terrain/derivatives.provenance.json"]
    if args.include_comparison:
        more = [f"data/raw/{args.site}/hirise_dtm_bxw_019698.tif",
                f"data/derived/{args.site}/hirise_019698_enu.tif",
                f"data/derived/{args.site}/hirise_019698_plan_4m.tif"]
        relative_paths += more
        metadata_paths += [str(Path(path).with_suffix(".provenance.json")).replace("\\", "/") for path in more]
        comparison_dir = root/f"data/derived/{args.site}/comparison"
        comparison_meta = json.loads((comparison_dir/"comparison.provenance.json").read_text(encoding="utf-8"))
        for asset in comparison_meta["assets"].values():
            relative_paths.append((comparison_dir/asset["href"]).relative_to(root).as_posix())
            metadata_paths.append((comparison_dir/asset["metadata"]).relative_to(root).as_posix())
        metadata_paths.append((comparison_dir/"comparison.provenance.json").relative_to(root).as_posix())
        relative_paths += [f"data/derived/{args.site}/qa_4m/qa.json", f"data/derived/{args.site}/qa_4m/qa.html"]
        relative_paths += ["docs/verification/T1_VERTICAL_DATUM.json", "docs/verification/T1_HIRISE_TRANSFER.json"]
        evidence = json.loads((root/"docs/verification/T1_VERTICAL_DATUM.json").read_text(encoding="utf-8"))
        for product in evidence["products"].values():
            relative_paths.extend((Path("docs/verification")/entry["path"]).as_posix() for entry in product["evidence"])
    relative_paths = list(dict.fromkeys(relative_paths))
    metadata_paths = list(dict.fromkeys(metadata_paths))
    assets = {path: {"sha256": digest(root/path), "bytes": (root/path).stat().st_size}
              for path in relative_paths + metadata_paths}
    reports = {path: json.loads((root/path).read_text(encoding="utf-8")) for path in metadata_paths}
    suites = list(ElementTree.parse(args.test_report).getroot().iter("testsuite"))
    counts = {key: sum(int(suite.get(key, 0)) for suite in suites) for key in ("tests", "errors", "failures", "skipped")}
    if counts["tests"] == 0 or any(counts[key] for key in ("errors", "failures", "skipped")):
        raise SystemExit("A nonempty green, zero-skip test report is required")
    source_files = list((root/"python/redline_data").rglob("*.py"))
    source_files += list((root/"python/redline_core").rglob("*.py"))
    source_files += [root/"config/sites.yaml", root/"config/products.yaml"]
    source_files += [root/"scripts"/name for name in ("common.sh", "bootstrap-data.sh", "requirements-data.txt",
        "test-data.sh", "run-t1.sh", "record_data_run.py", "probe_hirise_transfer.py")]
    result = {"schema": "redline-local-run-manifest/1", "is_stac_collection": False,
        "created_at": datetime.now(timezone.utc).isoformat(), "site_id": args.site,
        "status": "DERIVED", "python": platform.python_version(), "assets": assets,
        "metadata": reports, "tests": {"counts": counts, "report_sha256": digest(args.test_report),
            "report_path": args.test_report.resolve().relative_to(root).as_posix()},
        "source_code_sha256": {str(path.relative_to(root)).replace("\\", "/"): digest(path) for path in sorted(source_files)},
        "qa": json.loads((root/f"data/derived/{args.site}/qa_1m/qa.json").read_text(encoding="utf-8")),
        "milestone_T1_complete": False,
        "scope": "bounded local terrain pipeline; no independent elevation/alignment accuracy claim"}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(f"Recorded {len(assets)} artifacts, {counts['tests']} tests: {args.out}")


if __name__ == "__main__":
    main()
