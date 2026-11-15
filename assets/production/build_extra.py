"""Package the procedural props and extra CC0 rocks with the shared pipeline.

Usage: blender --background --factory-startup --python build_extra.py -- [ids]
build_package.py is reused unchanged: specs are registered at runtime with scale 1
(measured longest side). After each build, validate_package.py's per-asset Blender
checks are repeated for these ids only, plus rotation checks for every moving part
and a check that each prop's working side faces master +X. Results go to
verification_extra.json and each asset.json/SOURCE.md. Engine acceptance stays NOT_RUN.
"""
from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import build_package as bp  # noqa: E402
from preview import bounds  # noqa: E402

ROOT = bp.ROOT
PROCEDURAL = ("station_marker", "relay_mast", "equipment_cart", "valve_panel", "drone_pad", "rover_garage",
              "map_table", "console_desk", "lab_bench", "mission_wall", "storage_rack")
ROCKS = {"moon_rock_01": 4500, "moon_rock_03": 4500, "moon_rock_05": 4500, "namaqualand_boulder_04": 6000}
ROTATING = {"wheel": "Y", "valve_": "X", "needle": "X", "antenna": "Z"}  # master-frame rotation axes
# (front part, reference part): the front part's centroid must lie further along +X.
FRONT_CHECKS = {
    "station_marker": ("id_plate", "body_pole"), "relay_mast": ("body_box", "body_mast"),
    "equipment_cart": ("handle", "body_frame"), "valve_panel": ("valve_1", "body_panel"),
    "rover_garage": ("body_shell", "back_wall"), "console_desk": ("controls", "monitors"),
    "lab_bench": ("instrument", "body_bench"), "mission_wall": ("screen_wall", "body_frame"),
}


def measure(path: Path) -> tuple[float, int]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(path))
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    lo, hi = bounds(meshes)
    tris = sum(len(p.vertices) - 2 for o in meshes for p in o.data.polygons)
    return float(max(hi - lo)), tris


def spec_for(aid: str) -> dict:
    if aid in PROCEDURAL:
        longest, tris = measure(ROOT / "incoming" / aid / "source.glb")
        return {"source": "source.glb", "longest": longest, "lod0": tris, "gazebo": min(tris, 20000), "texture": 1024}
    longest, _ = measure(ROOT / "incoming" / aid / "source.gltf")
    return {"source": "source.gltf", "longest": longest, "lod0": ROCKS[aid], "gazebo": 800, "texture": 1024}


def centroid(objects, token):
    matches = [o for o in objects if f"_{token}_LOD0" in o.name]
    lo, hi = bounds(matches)
    return (lo + hi) * 0.5


def validate(aid: str) -> dict:
    folder = ROOT / "incoming" / aid
    data = json.loads((folder / "asset.json").read_text(encoding="utf-8"))
    bpy.ops.wm.open_mainfile(filepath=str(folder / "master.blend"), load_ui=False, use_scripts=False)
    objects = [o for o in bpy.context.scene.objects if o.type == "MESH" and o.name.startswith("SM_") and o.name.endswith("LOD0")]
    lo, hi = bounds(objects)
    expected = hi - lo
    result = {"master_loaded": True, "mesh_count": len(objects),
              "triangles": sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objects),
              "dimensions_m": list(expected),
              "source_metadata_dimensions_error_m": max(abs(a - b) for a, b in zip(expected, data["master"]["dimensions_m"])),
              "nonfinite_vertices": 0, "uv_missing_parts": [], "rotation_checks": []}
    if aid in FRONT_CHECKS:
        front, ref = FRONT_CHECKS[aid]
        result["front_is_plus_x"] = bool(centroid(objects, front).x > centroid(objects, ref).x)
    for o in objects:
        if not o.data.uv_layers:
            result["uv_missing_parts"].append(o.name)
        coords = np.empty(len(o.data.vertices) * 3)
        o.data.vertices.foreach_get("co", coords)
        result["nonfinite_vertices"] += int((~np.isfinite(coords)).sum())
        # Match on the part token only: the asset id prefix (e.g. "valve_panel") must not count.
        token = o.name[len(f"SM_{aid}_"):-len("_LOD0")].lower()
        key = next((k for k in ROTATING if token.startswith(k) or f"_{k}" in token), None)
        if key:
            o.rotation_mode = "XYZ"
            pivot = o.matrix_world.translation.copy()
            far = max(o.data.vertices, key=lambda v: v.co.length)
            point = o.matrix_world @ far.co
            basis = o.rotation_euler.copy()
            o.rotation_euler.rotate_axis(ROTATING[key], math.pi / 2)
            bpy.context.view_layer.update()
            result["rotation_checks"].append({
                "part": o.name, "axis": ROTATING[key], "angle_deg": 90,
                "pivot_drift_m": (o.matrix_world.translation - pivot).length,
                "vertex_displacement_m": (o.matrix_world @ far.co - point).length})
            o.rotation_euler = basis
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(folder / "unreal" / f"{aid}_LOD0.fbx"))
    imported = [o for o in bpy.context.scene.objects if o.type == "MESH" and not o.name.startswith("UCX_")]
    actual = bounds(imported)[1] - bounds(imported)[0]
    result["fbx_reimport"] = {"mesh_count": len(imported), "dimensions_m": list(actual),
                              "max_dimension_error_m": max(abs(a - b) for a, b in zip(expected, actual))}
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.obj_import(filepath=str(folder / "gazebo/assembly.obj"), forward_axis="Y", up_axis="Z")
    imported = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    actual = bounds(imported)[1] - bounds(imported)[0]
    result["obj_reimport"] = {"mesh_count": len(imported), "dimensions_m": list(actual),
                              "max_dimension_error_m": max(abs(a - b) for a, b in zip(expected, actual))}
    rotations_ok = all(r["pivot_drift_m"] < 1e-6 and r["vertex_displacement_m"] > 1e-4 for r in result["rotation_checks"])
    result["pass"] = bool(result["nonfinite_vertices"] == 0 and not result["uv_missing_parts"]
                          and result["fbx_reimport"]["max_dimension_error_m"] < 0.001
                          and result["obj_reimport"]["max_dimension_error_m"] < 0.04
                          and rotations_ok and result.get("front_is_plus_x", True))
    return result


def record(aid: str, spec: dict, result: dict) -> None:
    folder = ROOT / "incoming" / aid
    meta = folder / "asset.json"
    data = json.loads(meta.read_text(encoding="utf-8"))
    if aid in PROCEDURAL:
        generator = json.loads((folder / "generator.json").read_text(encoding="utf-8"))
        data["generator"] = generator
        data["source_notice"] = {"kind": "REDLINE prosedürel · özgün", "library": None, "tripo_tasks": [],
                                 "terms_urls": [], "note": "Original geometry from production/procedural_assets.py; "
                                 "no third-party mesh or generative AI."}
        data["limitations"] = ["SCENARIO engineering prop: dimensions are design choices, not measured hardware.",
                               "Flat PBR colours (textures only where noted); bevels, wear and decals are left to engine materials.",
                               "No mass, inertia, joint limits or controller; moving parts are presentation pivots only."]
        if aid == "valve_panel":
            data["limitations"].append("ArUco detection was verified on the source PNGs only; in-engine camera detection is NOT_RUN.")
    else:
        source = json.loads((folder / "download.json").read_text(encoding="utf-8"))
        data["source_notice"] = {"kind": "Poly Haven · CC0", "library": {k: source[k] for k in ("source", "credit", "license", "license_url")},
                                 "tripo_tasks": [], "terms_urls": [source["license_url"]]}
        data["limitations"] = ["CC0 terrestrial scan; shape and colour are not Mars mineral or measurement evidence."]
    data["build_spec"] = spec
    data["local_verification"] = result
    data["checks"]["local_file_roundtrip"] = "PASS" if result["pass"] else "FAIL"
    data["checks"]["engine_scale_calibration"] = "NOT_RUN; 1 m Blender FBX calibration exists in assets/calibration"
    data["delivery_status"] = "LOCAL_VISUAL_PACKAGE_PREPARED; ENGINE_ACCEPTANCE_PENDING"
    meta.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    notice = data["source_notice"]
    lines = [f"# {aid} — kaynak ve teslim kaydı", "", f"14 Kasım 2026 · {notice['kind']}.", ""]
    if aid in PROCEDURAL:
        gen = data["generator"]
        lines += [gen["purpose"] + ".", "", gen["notes"], "",
                  f"Kaynak: `production/procedural_assets.py` (SHA256 `{gen['generator']['sha256'][:16]}…`), "
                  "REDLINE için yazılmış özgün prosedürel geometri. Üçüncü taraf mesh veya üretken AI kullanılmadı. "
                  "Ölçüler SCENARIO tasarım seçimidir; gerçek donanım ölçüsü değildir.", ""]
        if aid == "valve_panel":
            aruco = gen["aruco"]
            lines += [f"ArUco: `{aruco['dictionary']}`, kimlikler {[m['id'] for m in aruco['markers']]}, işaret {aruco['marker_size_m']} m, "
                      f"plaka {aruco['plate_size_m']:.3f} m (1 hücre beyaz kenar). Desenler OpenCV {aruco['opencv']} ile üretildi ve PNG'den "
                      "yeniden okunarak doğrulandı. Motor dokusu sıkıştırmasız/filtresiz kullanılmalı.", ""]
    else:
        lib = notice["library"]
        lines += [f"Kaynak: [{lib['source']}]({lib['source']}). Atıf: {', '.join(lib['credit'])}. "
                  f"Kullanım: [{lib['license']}]({lib['license_url']}).", ""]
    lines += ["Teslim: `master.blend`, `presentation.glb`, `unreal/*LOD*.fbx`, `textures/`, `gazebo/assembly.obj`, parça OBJ'leri, "
              "basit çarpışma kutuları ve önizlemeler. Ortak master metre, sağ elli +X ileri/+Y sol/+Z yukarı.", "",
              f"Ölçülen LOD0: {data['lod0']['triangles']:,} üçgen; {len(data['parts'])} parça. Gazebo visual: {data['gazebo']['triangles']:,} üçgen.", "",
              f"Yerel yeniden içe aktarma ve pivot kontrolleri: **{'geçti' if result['pass'] else 'BAŞARISIZ'}**. "
              "Unreal/Gazebo içi import, 100 cm/1 m ölçümü ve materyal bağlama: **yapılmadı**.", "",
              "Açık sınırlar:", ""] + ["- " + x for x in data["limitations"]]
    (folder / "SOURCE.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ids = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ids = ids or [*PROCEDURAL, *ROCKS]
    report_path = ROOT / "verification_extra.json"
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {"assets": {}}
    report.update({"created_utc": datetime.now(timezone.utc).isoformat(), "blender": bpy.app.version_string,
                   "scope": "Blender file/geometry evidence for the extra packages only; mirrors validate_package.py "
                            "plus moving-part pivot and +X front checks. No engine import or robot dynamics."})
    for aid in ids:
        spec = spec_for(aid)
        bp.SPECS[aid] = spec
        bp.build(aid)
        result = validate(aid)
        record(aid, spec, result)
        report["assets"][aid] = result
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print("EXTRA_VALIDATED", aid, result["pass"], "front", result.get("front_is_plus_x"),
              "rotations", len(result["rotation_checks"]), "FBX", f"{result['fbx_reimport']['max_dimension_error_m']:.2e}", flush=True)


if __name__ == "__main__":
    main()
