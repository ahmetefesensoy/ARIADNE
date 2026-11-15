"""Explicit data commands; errors never become fabricated successful products."""
import argparse
from collections.abc import Sequence
import json
from pathlib import Path
import sys

from redline_data import __version__


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="redline-data",
        description="REDLINE T1 bounded planetary data pipeline.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command")
    catalog_parser = commands.add_parser("catalog", help="HEAD-only source availability, not scientific validation")
    catalog_parser.add_argument("--products", type=Path, default=Path("config/products.yaml"))
    catalog_parser.add_argument("--site")
    catalog_parser.add_argument("--product", action="append")
    catalog_parser.add_argument("--out", type=Path)
    fetch_parser = commands.add_parser("fetch", help="Bounded source-aligned raster window")
    fetch_parser.add_argument("--products", type=Path, default=Path("config/products.yaml"))
    fetch_parser.add_argument("--sites", type=Path, default=Path("config/sites.yaml"))
    fetch_parser.add_argument("--site", required=True)
    fetch_parser.add_argument("--product", required=True)
    fetch_parser.add_argument("--expected-radius-m", required=True, type=float,
                              help="Explicit product expectation; actual WKT is checked against it")
    fetch_parser.add_argument("--expected-lon-0", type=float, default=0)
    fetch_parser.add_argument("--expected-lat-ts", type=float, default=0)
    fetch_parser.add_argument("--size-m", type=float, nargs=2, metavar=("WIDTH", "HEIGHT"),
                              help="Explicit smaller diagnostic AOI override, recorded in provenance")
    fetch_parser.add_argument("--out", type=Path, required=True)
    crs_parser = commands.add_parser("crs", help="Inspect and verify horizontal product WKT")
    crs_parser.add_argument("path", type=Path)
    crs_parser.add_argument("--expected-radius-m", required=True, type=float)
    crs_parser.add_argument("--expected-lon-0", type=float, default=0)
    crs_parser.add_argument("--expected-lat-ts", type=float, default=0)
    crs_parser.add_argument("--out", type=Path)
    enu_parser = commands.add_parser("enu", help="Spec local metric approximation with explicit origin")
    enu_parser.add_argument("path", type=Path)
    enu_parser.add_argument("--sites", type=Path, default=Path("config/sites.yaml"))
    enu_parser.add_argument("--site", required=True)
    enu_parser.add_argument("--expected-radius-m", required=True, type=float)
    enu_parser.add_argument("--expected-lon-0", type=float, default=0)
    enu_parser.add_argument("--expected-lat-ts", type=float, default=0)
    enu_parser.add_argument("--h0-m", type=float, required=True, help="Explicit scenario origin offset, not a vertical datum")
    enu_parser.add_argument("--resolution-m", type=float, required=True)
    enu_parser.add_argument("--size-m", type=float, nargs=2)
    enu_parser.add_argument("--kind", choices=("dem", "class"), default="dem")
    enu_parser.add_argument("--out", required=True, type=Path)
    derive_parser = commands.add_parser("derive", help="Source-grid multi-baseline slopes and plane-residual roughness")
    derive_parser.add_argument("path", type=Path)
    derive_parser.add_argument("--baselines-m", nargs="+", type=float, default=[2, 5])
    derive_parser.add_argument("--roughness-radius-m", type=float, default=2)
    derive_parser.add_argument("--out", required=True, type=Path)
    qa_parser = commands.add_parser("qa", help="Source-to-local numerical transfer checks; no ground-truth claim")
    qa_parser.add_argument("source", type=Path)
    qa_parser.add_argument("local", type=Path)
    qa_parser.add_argument("--terrain", type=Path)
    qa_parser.add_argument("--out", required=True, type=Path)
    compare_parser = commands.add_parser("compare", help="Bounded relative DEM registration and empirical slope disagreement")
    compare_parser.add_argument("primary", type=Path)
    compare_parser.add_argument("reference", type=Path)
    compare_parser.add_argument("primary_fit", type=Path)
    compare_parser.add_argument("reference_fit", type=Path)
    compare_parser.add_argument("--vertical-evidence", required=True, type=Path)
    compare_parser.add_argument("--max-shift-m", type=float, default=20)
    compare_parser.add_argument("--out", required=True, type=Path)
    stac_parser = commands.add_parser("stac", help="Local processing-time Mars STAC Collection and Items")
    stac_parser.add_argument("--site", required=True)
    stac_parser.add_argument("--manifest", required=True, type=Path)
    stac_parser.add_argument("--out", required=True, type=Path)
    validation_parser = commands.add_parser("stac-validate", help="Validate local STAC using pinned offline official schemas")
    validation_parser.add_argument("path", type=Path)
    validation_parser.add_argument("--schema-root", type=Path,
        default=Path(__file__).resolve().parents[2] / "tests" / "schemas")
    validation_parser.add_argument("--out", type=Path)
    acceptance_parser = commands.add_parser("qa-final", help="Recheck frozen BXW T1 data, tests and offline STAC acceptance")
    acceptance_parser.add_argument("--manifest", required=True, type=Path)
    acceptance_parser.add_argument("--stac", required=True, type=Path)
    acceptance_parser.add_argument("--schema-root", type=Path,
        default=Path(__file__).resolve().parents[2] / "tests" / "schemas")
    acceptance_parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    try:
        if args.command == "catalog":
            from .catalog import build
            report = build(args.products, site_id=args.site, product_keys=tuple(args.product) if args.product else None)
            result = report.to_dict()
            code = 0 if report.ok else 1
        elif args.command == "fetch":
            from .catalog import load_products, load_sites
            from .crs import ExpectedCrs
            from .fetch import WindowRequest, extract_window
            products = {p.key: p for p in load_products(args.products)}
            sites = load_sites(args.sites)
            if args.product not in products or args.site not in sites:
                raise ValueError("Unknown product/site key")
            product, site = products[args.product], sites[args.site]
            if args.site not in product.sites or not product.url.lower().endswith((".tif", ".tiff")):
                raise ValueError("Product is not a raster candidate for this site")
            request = WindowRequest(site.site_id, site.center_lat, site.center_lon_east,
                                    tuple(args.size_m) if args.size_m else site.size_m)
            result = extract_window(product.url, request,
                ExpectedCrs(args.expected_radius_m, args.expected_lon_0, args.expected_lat_ts),
                args.out, product_id=product.product_id)
            code = 0
        elif args.command == "enu":
            from .catalog import load_sites
            from .crs import ExpectedCrs
            from .enu import to_local
            sites = load_sites(args.sites)
            if args.site not in sites:
                raise ValueError("Unknown site key")
            site = sites[args.site]
            result = to_local(args.path, center_lat=site.center_lat, center_lon_east=site.center_lon_east,
                h0_m=args.h0_m, resolution_m=args.resolution_m, destination=args.out,
                expected=ExpectedCrs(args.expected_radius_m, args.expected_lon_0, args.expected_lat_ts),
                size_m=tuple(args.size_m) if args.size_m else site.size_m, kind=args.kind)
            code = 0
        elif args.command == "derive":
            from .derive import write_products
            result = write_products(args.path, args.out, baselines_m=args.baselines_m,
                                    radius_m=args.roughness_radius_m)
            code = 0
        elif args.command == "qa":
            from .qa import report
            result = report(args.source, args.local, destination=args.out, terrain=args.terrain)
            code = 0 if result["numerical_checks_passed"] else 1
        elif args.command == "compare":
            from .compare import compare_dems
            result = compare_dems(args.primary, args.reference, args.primary_fit, args.reference_fit,
                destination=args.out, vertical_evidence=args.vertical_evidence, max_shift_m=args.max_shift_m)
            code = 0
        elif args.command == "stac":
            from .stac import write
            result = write(args.site, manifest_path=args.manifest, destination=args.out, root=Path.cwd())
            code = 0
        elif args.command == "stac-validate":
            from .stac import validate
            result = validate(args.path, schema_root=args.schema_root)
            code = 0
        elif args.command == "qa-final":
            from .acceptance import check_t1
            result = check_t1(root=Path.cwd(), manifest_path=args.manifest,
                stac_directory=args.stac, schema_root=args.schema_root, destination=args.out)
            code = 0 if result["passed"] else 1
        else:
            import rasterio
            from .crs import ExpectedCrs, check_wkt
            with rasterio.open(args.path) as source:
                result = check_wkt(source.crs.to_wkt() if source.crs else None,
                    ExpectedCrs(args.expected_radius_m, args.expected_lon_0, args.expected_lat_ts))
            code = 0
        if args.command in ("catalog", "crs", "stac-validate") and args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2))
        return code
    except ImportError as error:
        print(f"Missing optional data dependency: {error}. Run scripts/bootstrap-data.sh", file=sys.stderr)
        return 2
    except (ValueError, OSError) as error:
        print(f"redline-data: {error}", file=sys.stderr)
        return 1
