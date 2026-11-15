"""Small analytic fixtures for terrain geometry, frame, masks and cache safety."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin


SCRIPT = Path(__file__).resolve().parents[1] / "export_t3_terrain.py"
SPEC = importlib.util.spec_from_file_location("redline_t3_export", SCRIPT)
terrain = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = terrain
SPEC.loader.exec_module(terrain)


def write_dem(path: Path, resolution: int, *, kind: str = "plane", invalid: tuple[int, int] | None = None) -> Path:
    size = 20 // resolution
    transform = from_origin(-10, 10, resolution, resolution)
    cols, rows = np.meshgrid(np.arange(size), np.arange(size))
    x, y = -10 + (cols+0.5)*resolution, 10 - (rows+0.5)*resolution
    values = -3600 + 0.01*x + 0.02*y if kind == "plane" else -3600 + 2*x*y
    values = values.astype("float32")
    if invalid is not None:
        values[invalid] = np.nan
    with rasterio.open(path, "w", driver="GTiff", width=size, height=size, count=1,
                       dtype="float32", nodata=np.nan, transform=transform) as dst:
        dst.write(values, 1)
        dst.update_tags(FRAME="map", HORIZONTAL_UNITS="m", PROVENANCE_STATUS="DERIVED")
    sidecar = {"sha256": terrain.sha256(path), "status": "DERIVED", "frame": "map", "units": "m",
               "origin": {"E0_m": 8142565.198776576, "N0_m": -284814.9215994864,
                          "H0_m": 0.0, "status": "SCENARIO"},
               "identity": {"center_lat": -4.805, "center_lon_east": 137.37,
                            "expected": {"sphere_radius_m": 3396190, "lon_0_deg": 0, "lat_ts_deg": 0}},
               "source_wkt": "source planetary CRS retained by fixture"}
    path.with_suffix(".provenance.json").write_text(json.dumps(sidecar), encoding="utf-8")
    return path


@pytest.fixture
def inputs(tmp_path):
    return write_dem(tmp_path/"fine.tif", 1), write_dem(tmp_path/"coarse.tif", 4)


def load_obj(path: Path, pose: list[float]) -> tuple[np.ndarray, np.ndarray]:
    vertices, faces = [], []
    for line in path.read_text(encoding="ascii").splitlines():
        if line.startswith("v "):
            vertices.append(tuple(map(float, line.split()[1:])))
        elif line.startswith("f "):
            faces.append(tuple(int(value.split("//")[0])-1 for value in line.split()[1:]))
    return np.asarray(vertices) + np.asarray(pose[:3]), np.asarray(faces)


def export(inputs, out):
    return terrain.export_terrain(*inputs, out, ops_size=8, tile_size=4, goal_distance_m=2)


def test_plane_export_preserves_negative_map_z_and_nonoverlapping_upward_geometry(inputs, tmp_path):
    out = tmp_path/"gazebo"
    manifest = export(inputs, out)
    assert manifest["engine_z_offset_m"] == 0
    assert manifest["map_origin"]["H0_m"] == 0
    assert len(manifest["meshes"]) == 5  # four small ops tiles + one ring
    assert manifest["qa"]["three_point_passed"]
    area = 0.0
    for mesh in manifest["meshes"]:
        assert mesh["visual_uri"] == mesh["collision_uri"]
        vertices, faces = load_obj(out/mesh["relative_path"], mesh["pose_map_m"])
        assert vertices[:, 2].max() < -3500
        # A plane has no resampling/triangulation ambiguity at any vertex.
        assert np.max(np.abs(vertices[:, 2] - (-3600+0.01*vertices[:, 0]+0.02*vertices[:, 1]))) < 0.0003
        triangles = vertices[faces]
        cross = np.cross(triangles[:, 1]-triangles[:, 0], triangles[:, 2]-triangles[:, 0])
        assert (cross[:, 2] > 0).all()
        area += float(cross[:, 2].sum())/2
        centroids = triangles[:, :, :2].mean(axis=1)
        if mesh["role"] == "surround_4m":
            assert not ((np.abs(centroids[:, 0]) < 4) & (np.abs(centroids[:, 1]) < 4)).any()
    # Positive triangle orientation + exact partition area catches missing or
    # doubled strips at the dense/coarse seam on this fixture.
    assert area == pytest.approx(19*19)
    assert manifest["spawn"]["ground_z_m"] < -3500
    assert manifest["scenario"]["max_fine_slope_deg"] < 3
    dx = manifest["goal"]["map_x_m"]-manifest["spawn"]["map_x_m"]
    dy = manifest["goal"]["map_y_m"]-manifest["spawn"]["map_y_m"]
    assert np.hypot(dx, dy) == pytest.approx(2)
    pgm = (out/manifest["nav"]["image"]).read_bytes().split(b"\n", 3)[-1]
    image = np.frombuffer(pgm, dtype="uint8").reshape((5, 5))
    assert (image[0] == 0).all() and (image[-1] == 0).all()
    assert image[2, 2] == 254


def test_ops_and_ring_share_dense_edges_and_serialize_identical_heights(inputs, tmp_path):
    out = tmp_path/"gazebo"
    manifest = export(inputs, out)
    meshes = [load_obj(out/m["relative_path"], m["pose_map_m"]) for m in manifest["meshes"]]
    ring = meshes[-1][0]
    for value, column in ((-4, 0), (4, 0), (-4, 1), (4, 1)):
        other = 1-column
        ring_edge = ring[np.isclose(ring[:, column], value) & (np.abs(ring[:, other]) <= 4)]
        fine_vertices = np.concatenate([v for v, _ in meshes[:-1]])
        fine_edge = fine_vertices[np.isclose(fine_vertices[:, column], value)]
        for position in np.arange(-4, 5):
            a = ring_edge[np.isclose(ring_edge[:, other], position)]
            b = fine_edge[np.isclose(fine_edge[:, other], position)]
            assert len(a) and len(b)
            assert a[:, 2].max()-a[:, 2].min() < 1e-6
            assert np.max(np.abs(a[:, 2, None] - b[:, 2])) <= 1.1e-6


def test_every_imported_face_position_has_explicit_unit_upward_normal(inputs, tmp_path):
    out = tmp_path/"gazebo"
    manifest = export(inputs, out)
    assert manifest["identity"]["algorithm"] == "redline-t3-terrain-v2"
    for mesh in manifest["meshes"]:
        normals, face_positions, face_normals = [], [], []
        vertices = 0
        for line in (out/mesh["relative_path"]).read_text(encoding="ascii").splitlines():
            if line.startswith("v "):
                vertices += 1
            elif line.startswith("vn "):
                normals.append(tuple(map(float, line.split()[1:])))
            elif line.startswith("f "):
                pairs = [tuple(map(int, value.split("//"))) for value in line.split()[1:]]
                face_positions.append([v for v, _ in pairs])
                face_normals.append([n for _, n in pairs])
        normals = np.asarray(normals)
        assert len(normals) == vertices == mesh["normals"] == mesh["vertices"]
        assert np.isfinite(normals).all()
        assert np.allclose(np.linalg.norm(normals, axis=1), 1.0, atol=2e-9, rtol=0)
        assert (normals[:, 2] > 0).all()
        assert np.array_equal(face_positions, face_normals)
        indices = np.asarray(face_normals)-1
        assert indices.min() >= 0 and indices.max() < len(normals)
        expanded = normals[indices].reshape((-1, 3))
        assert len(expanded) == 3*mesh["triangles"]


def test_zipper_fills_dense_to_coarse_strip_without_degenerate_faces():
    lower = np.arange(9)
    upper = np.array([0, 4, 8])
    vertices = np.concatenate((np.column_stack((lower, np.zeros(9))), np.column_stack((upper, np.ones(3)))))
    faces = terrain.zipper_faces(lower, upper, np.arange(9), 9+np.arange(3))
    tri = vertices[faces]
    area2 = np.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0])
    assert (area2 > 0).all()
    assert area2.sum()/2 == pytest.approx(8)
    assert len(faces) == 10


def test_masks_never_turn_into_flat_collision_or_free_nav_cells(tmp_path):
    fine_path = write_dem(tmp_path/"fine.tif", 1, invalid=(10, 10))
    coarse_path = write_dem(tmp_path/"coarse.tif", 4, invalid=(2, 2))
    fine, coarse = terrain.Surface.open(fine_path, 1, 1000), terrain.Surface.open(coarse_path, 4, 1000)
    try:
        z, valid = fine.sample(np.array([0.5]), np.array([-0.5]))
        assert not valid[0] and np.isnan(z[0])
        vertices, faces = terrain.ops_mesh(fine, (-4, -4, 4, 4))
        assert len(faces) < 2*8*8
        assert np.isfinite(vertices[faces]).all()
        nav, free = terrain.nav_map(coarse, tmp_path, 20)
        assert not free[2, 2]
        assert nav["free_cells"] == 0  # centre nodata poisons each internal 3x3 stencil
    finally:
        fine.dataset.close()
        coarse.dataset.close()


def test_cache_validates_sources_and_artifact_hashes_without_overwriting(inputs, tmp_path):
    out = tmp_path/"gazebo"
    first = export(inputs, out)
    before = {p.name: p.stat().st_mtime_ns for p in out.iterdir()}
    second = export(inputs, out)
    assert second["cache_hit"] and first["identity"] == second["identity"]
    assert before == {p.name: p.stat().st_mtime_ns for p in out.iterdir()}
    with pytest.raises(FileExistsError, match="different source/configuration"):
        terrain.export_terrain(*inputs, out, ops_size=8, tile_size=4, goal_distance_m=1)
    (out/first["meshes"][0]["relative_path"]).write_text("corrupt", encoding="ascii")
    with pytest.raises(ValueError, match="artifact hash"):
        export(inputs, out)


def test_budgets_and_frame_fail_before_export(inputs, tmp_path):
    with pytest.raises(ValueError, match="pixel budget"):
        terrain.export_terrain(*inputs, tmp_path/"small-budget", max_source_pixels=10)
    with pytest.raises(ValueError, match="triangle budget"):
        terrain.export_terrain(*inputs, tmp_path/"face-budget", ops_size=8, tile_size=4,
                               goal_distance_m=2, max_triangles=10)
    sidecar = inputs[1].with_suffix(".provenance.json")
    metadata = json.loads(sidecar.read_text(encoding="utf-8"))
    metadata["origin"]["H0_m"] = -3600
    sidecar.write_text(json.dumps(metadata), encoding="utf-8")
    with pytest.raises(ValueError, match="different map origins"):
        export(inputs, tmp_path/"bad-frame")
    assert not (tmp_path/"bad-frame").exists()


def test_source_hash_and_no_extrapolation(inputs):
    fine = terrain.Surface.open(inputs[0], 1, 1000)
    try:
        with pytest.raises(ValueError, match="pixel-centre support"):
            fine.sample(np.array([-10.0]), np.array([0.0]))
    finally:
        fine.dataset.close()
    with inputs[0].open("ab") as stream:
        stream.write(b"changed")
    with pytest.raises(ValueError, match="Source hash"):
        terrain.Surface.open(inputs[0], 1, 1000)


def test_nonplanar_triangle_error_is_observed_rather_than_assumed_zero(tmp_path):
    path = write_dem(tmp_path/"saddle.tif", 1, kind="saddle")
    fine = terrain.Surface.open(path, 1, 1000)
    try:
        x, y = 0.5, 0.5
        bilinear, _ = fine.sample(np.array([x]), np.array([y]))
        triangle = terrain.triangle_height(fine, x, y, (-4, -4, 4, 4))
        assert abs(float(bilinear[0])-triangle) > 0.1
    finally:
        fine.dataset.close()
