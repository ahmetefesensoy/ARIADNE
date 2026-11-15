#!/usr/bin/env python3
"""Export bounded T3 physics terrain and a scenario Nav2 smoke-test map.

This helper reads verified local ENU rasters; it does not implement T2 planning,
download data, author a world, or alter source rasters. Mesh vertices use metres
in the existing map frame. Visual and collision consumers use the same OBJ.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import rasterio
from rasterio.windows import Window


ALGORITHM = "redline-t3-terrain-v2"
MESH_DECIMALS = 6


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def axis(low: float, high: float, spacing: float) -> np.ndarray:
    """Endpoints plus a global metre lattice, so adjacent patches share edges."""
    if not (math.isfinite(low + high + spacing) and low < high and spacing > 0):
        raise ValueError("Invalid mesh axis")
    middle = np.arange(math.ceil(low / spacing), math.floor(high / spacing) + 1) * spacing
    return np.unique(np.concatenate(([low], middle, [high])))


def full_window_true(mask: np.ndarray, side: int) -> np.ndarray:
    """Valid only where a complete odd square support is true; borders are false."""
    if side < 1 or side % 2 != 1:
        raise ValueError("Support window must be odd and positive")
    result = np.zeros_like(mask, dtype=bool)
    if min(mask.shape) < side:
        return result
    sums = np.pad(mask.astype("int32"), ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    counts = sums[side:, side:] - sums[:-side, side:] - sums[side:, :-side] + sums[:-side, :-side]
    radius = side // 2
    result[radius : mask.shape[0] - radius or None, radius : mask.shape[1] - radius or None] = counts == side * side
    return result


def slope_degrees(values: np.ndarray, valid: np.ndarray, resolution: float) -> tuple[np.ndarray, np.ndarray]:
    """Central finite differences, with a conservative complete 3x3 stencil."""
    if min(values.shape) < 3:
        return np.full(values.shape, np.nan), np.zeros(values.shape, bool)
    safe = np.where(valid, values, 0.0)
    dy, dx = np.gradient(safe, resolution, resolution)
    supported = full_window_true(valid & np.isfinite(values), 3)
    slope = np.degrees(np.arctan(np.hypot(dx, dy)))
    return np.where(supported, slope, np.nan), supported


@dataclass
class Surface:
    path: Path
    dataset: object
    metadata: dict
    digest: str
    sidecar_digest: str
    max_pixels: int

    @classmethod
    def open(cls, path: Path, resolution: float, max_pixels: int) -> "Surface":
        sidecar = path.with_suffix(".provenance.json")
        metadata = json.loads(sidecar.read_text(encoding="utf-8"))
        digest = sha256(path)
        if metadata.get("sha256") != digest:
            raise ValueError(f"Source hash does not match its provenance: {path}")
        if metadata.get("frame") != "map" or metadata.get("units") != "m" or metadata.get("status") != "DERIVED":
            raise ValueError("Verified DERIVED map-frame/metre provenance is required")
        origin = metadata.get("origin", {})
        if not all(math.isfinite(origin.get(k, float("nan"))) for k in ("E0_m", "N0_m", "H0_m")):
            raise ValueError("Explicit finite E0/N0/H0 is required")
        dataset = rasterio.open(path)
        try:
            t = dataset.transform
            if dataset.crs is not None:
                raise ValueError("Expected local ENU raster without an invented projected CRS")
            if dataset.count != 1 or not np.issubdtype(np.dtype(dataset.dtypes[0]), np.floating):
                raise ValueError("Single-band floating-point elevation raster required")
            if not np.allclose((t.a, t.b, t.d, t.e), (resolution, 0, 0, -resolution), rtol=0, atol=1e-9):
                raise ValueError(f"Expected north-up {resolution:g} m local grid")
            if dataset.width * dataset.height > max_pixels:
                raise ValueError("Source pixel budget exceeded")
            if dataset.scales != (1.0,) or dataset.offsets != (0.0,):
                raise ValueError("Elevation scale/offset must already be applied")
            if dataset.tags().get("FRAME") != "map" or dataset.tags().get("HORIZONTAL_UNITS") != "m":
                raise ValueError("Raster frame/unit tags disagree with sidecar")
            return cls(path, dataset, metadata, digest, sha256(sidecar), max_pixels)
        except Exception:
            dataset.close()
            raise

    @property
    def domain(self) -> tuple[float, float, float, float]:
        """Bilinear support between pixel centres, not outer raster edges."""
        d = self.dataset
        return (d.bounds.left + d.res[0] / 2, d.bounds.bottom + d.res[1] / 2,
                d.bounds.right - d.res[0] / 2, d.bounds.top - d.res[1] / 2)

    def sample(self, x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        x, y = np.broadcast_arrays(np.asarray(x, float), np.asarray(y, float))
        original_shape = x.shape
        d = self.dataset
        cols = (x.ravel() - d.transform.c) / d.transform.a - 0.5
        rows = (y.ravel() - d.transform.f) / d.transform.e - 0.5
        inside = (cols >= -1e-7) & (cols <= d.width - 1 + 1e-7) & (rows >= -1e-7) & (rows <= d.height - 1 + 1e-7)
        if not inside.all():
            raise ValueError("Sampling outside the source pixel-centre support is forbidden")
        cols, rows = np.clip(cols, 0, d.width - 1), np.clip(rows, 0, d.height - 1)
        c0, r0 = np.floor(cols).astype(int), np.floor(rows).astype(int)
        c1, r1 = np.minimum(c0 + 1, d.width - 1), np.minimum(r0 + 1, d.height - 1)
        left, top = int(c0.min()), int(r0.min())
        width, height = int(c1.max()) - left + 1, int(r1.max()) - top + 1
        if width * height > self.max_pixels:
            raise ValueError("Sample read window exceeds source pixel budget")
        window = Window(left, top, width, height)
        z = d.read(1, window=window).astype("float64")
        mask = (d.read_masks(1, window=window) != 0) & np.isfinite(z)
        fx, fy = cols - c0, rows - r0
        result, valid = np.zeros(cols.shape), np.ones(cols.shape, bool)
        for rr, cc, weight in ((r0, c0, (1-fx)*(1-fy)), (r0, c1, fx*(1-fy)),
                               (r1, c0, (1-fx)*fy), (r1, c1, fx*fy)):
            values = z[rr - top, cc - left]
            supported = mask[rr - top, cc - left]
            needed = weight > 1e-12
            valid &= ~needed | supported
            result += np.where(supported, values, 0) * weight
        return np.where(valid, result, np.nan).reshape(original_shape), valid.reshape(original_shape)

    def info(self) -> dict:
        return {"path": self.path.as_posix(), "sha256": self.digest,
                "provenance_path": self.path.with_suffix(".provenance.json").as_posix(),
                "provenance_sha256": self.sidecar_digest,
                "shape": [self.dataset.height, self.dataset.width],
                "transform": list(self.dataset.transform), "source_wkt": self.metadata.get("source_wkt"),
                "origin": self.metadata["origin"], "frame": "map", "units": "m"}


def regular_faces(rows: int, cols: int) -> np.ndarray:
    a = (np.arange(rows - 1)[:, None] * cols + np.arange(cols - 1)).ravel()
    return np.concatenate((np.column_stack((a, a+1, a+cols)), np.column_stack((a+1, a+cols+1, a+cols))))


def zipper_faces(lower: np.ndarray, upper: np.ndarray, lower_ids: np.ndarray, upper_ids: np.ndarray) -> np.ndarray:
    """Triangulate one strip with unequal edge subdivisions, without T junctions."""
    if not np.allclose((lower[0], lower[-1]), (upper[0], upper[-1]), atol=1e-9, rtol=0):
        raise ValueError("Strip endpoints must agree")
    i = j = 0
    faces = []
    while i + 1 < len(lower) or j + 1 < len(upper):
        a = lower[i+1] if i+1 < len(lower) else np.inf
        b = upper[j+1] if j+1 < len(upper) else np.inf
        if a <= b:
            faces.append((lower_ids[i], lower_ids[i+1], upper_ids[j]))
            i += 1
        else:
            faces.append((lower_ids[i], upper_ids[j+1], upper_ids[j]))
            j += 1
    return np.asarray(faces, dtype="int64")


def ops_mesh(fine: Surface, bounds: tuple[float, float, float, float]) -> tuple[np.ndarray, np.ndarray]:
    x0, y0, x1, y1 = bounds
    xx, yy = np.meshgrid(axis(x0, x1, 1), axis(y0, y1, 1))
    zz, valid = fine.sample(xx, yy)
    vertices = np.column_stack((xx.ravel(), yy.ravel(), zz.ravel()))
    faces = regular_faces(*xx.shape)
    faces = faces[valid.ravel()[faces].all(axis=1)]
    return vertices, faces


def ring_patch(fine: Surface, coarse: Surface, name: str, outer: tuple, ops: tuple) -> tuple[np.ndarray, np.ndarray, dict]:
    left, bottom, right, top = outer
    west, south, east, north = ops
    if name in ("north", "south"):
        low, high = left, right
        near, far = (north, top) if name == "north" else (-south, -bottom)
        dense = axis(west, east, 1)
        regular = axis(left, right, 4)
        regular = np.unique(np.concatenate((regular, [west, east])))
        boundary = np.unique(np.concatenate((regular[(regular < west) | (regular > east)], dense)))
    else:
        low, high = south, north
        near, far = (-west, -left) if name == "west" else (east, right)
        regular, boundary = axis(low, high, 4), axis(low, high, 1)
    v = axis(near, far, 4)
    # The entire first strip is triangulated against the finer edge. All
    # subsequent rows retain the coarse lattice. Adjacent patches share both
    # the boundary coordinates and the source used at those coordinates.
    uv0 = np.column_stack((boundary, np.full(boundary.shape, v[0])))
    uu, vv = np.meshgrid(regular, v[1:])
    uv = np.concatenate((uv0, np.column_stack((uu.ravel(), vv.ravel()))))
    u, vv = uv[:, 0], uv[:, 1]
    if name == "north":
        x, y, reverse = u, vv, False
    elif name == "south":
        x, y, reverse = u, -vv, True
    elif name == "west":
        x, y, reverse = -vv, u, False
    else:
        x, y, reverse = vv, u, True
    # Shared inner seam is 1m DEM; outer support beyond 4m pixel centres
    # also uses 1m DEM. This extends no source beyond its valid support.
    c_left, c_bottom, c_right, c_top = coarse.domain
    on_ops = (((np.isclose(x, west) | np.isclose(x, east)) & (y >= south) & (y <= north)) |
              ((np.isclose(y, south) | np.isclose(y, north)) & (x >= west) & (x <= east)))
    use_fine = on_ops | (x < c_left) | (x > c_right) | (y < c_bottom) | (y > c_top)
    z, valid = np.full(x.shape, np.nan), np.zeros(x.shape, bool)
    for surface, selected in ((fine, use_fine), (coarse, ~use_fine)):
        if selected.any():
            z[selected], valid[selected] = surface.sample(x[selected], y[selected])
    vertices = np.column_stack((x, y, z))
    n_boundary, n_regular = len(boundary), len(regular)
    strip = zipper_faces(boundary, regular, np.arange(n_boundary), n_boundary + np.arange(n_regular))
    faces = strip
    if len(v) > 2:
        faces = np.concatenate((strip, regular_faces(len(v)-1, n_regular) + n_boundary))
    if reverse:
        faces = faces[:, (0, 2, 1)]
    faces = faces[valid[faces].all(axis=1)]
    return vertices, faces, {"patch": name, "fine_boundary_vertices": int(use_fine.sum()),
                              "invalid_vertices": int((~valid).sum())}


def write_obj(path: Path, vertices: np.ndarray, faces: np.ndarray, origin: np.ndarray) -> dict:
    """Write only supported triangles, and keep local vertex magnitudes small."""
    used, inverse = np.unique(faces, return_inverse=True)
    compact = vertices[used]
    local = compact - origin
    faces = inverse.reshape((-1, 3))
    if not len(faces) or not np.isfinite(local).all():
        raise ValueError("Empty or non-finite terrain mesh")
    # Gazebo's DART custom-mesh importer requires a normal for every imported
    # position. Explicit v//vn indices survive its per-face vertex expansion;
    # relying on an OBJ loader to synthesize normals can leave collision empty.
    # Area-weighted sums preserve the actual triangle winding and are bounded
    # by a fixed face chunk rather than allocating all face coordinates at once.
    normals = np.zeros_like(local)
    for start in range(0, len(faces), 32768):
        chunk = faces[start:start+32768]
        edge1 = local[chunk[:, 1]] - local[chunk[:, 0]]
        edge2 = local[chunk[:, 2]] - local[chunk[:, 0]]
        area_normals = np.cross(edge1, edge2)
        if not np.isfinite(area_normals).all() or (area_normals[:, 2] <= 0).any():
            raise ValueError("Terrain faces must have finite, nonzero upward normals")
        for corner in range(3):
            np.add.at(normals, chunk[:, corner], area_normals)
    lengths = np.linalg.norm(normals, axis=1)
    if not np.isfinite(lengths).all() or (lengths <= 0).any():
        raise ValueError("Every used terrain vertex must have a valid normal")
    normals /= lengths[:, None]
    faces = faces + 1
    with path.open("w", encoding="ascii", newline="\n") as out:
        out.write("# REDLINE DERIVED physics terrain; metres; map pose in manifest.json\n")
        for start in range(0, len(local), 8192):
            out.writelines("v %.6f %.6f %.6f\n" % tuple(row) for row in local[start:start+8192])
        for start in range(0, len(normals), 8192):
            out.writelines("vn %.9f %.9f %.9f\n" % tuple(row) for row in normals[start:start+8192])
        for start in range(0, len(faces), 8192):
            out.writelines(f"f {a}//{a} {b}//{b} {c}//{c}\n" for a, b, c in faces[start:start+8192])
    projected = vertices[used, :2]
    return {"relative_path": path.name, "visual_uri": path.name, "collision_uri": path.name,
            "pose_map_m": [float(v) for v in origin] + [0.0, 0.0, 0.0],
            "vertices": len(local), "triangles": len(faces), "sha256": sha256(path),
            "normals": len(normals), "normal_encoding": "area-weighted unit vertex normals; f vertex//normal indices",
            "bounds_map_m": [float(projected[:, 0].min()), float(projected[:, 1].min()),
                             float(projected[:, 0].max()), float(projected[:, 1].max())],
            "z_bounds_map_m": [float(compact[:, 2].min()), float(compact[:, 2].max())],
            "visual_collision_identical": True}


def nav_map(coarse: Surface, directory: Path, threshold: float) -> tuple[dict, np.ndarray]:
    d = coarse.dataset
    values = d.read(1).astype("float64")
    valid = (d.read_masks(1) != 0) & np.isfinite(values)
    slope, supported = slope_degrees(values, valid, 4.0)
    free = supported & (slope < threshold)
    image = np.where(free, 254, 0).astype("uint8")
    image_path = directory / "nav_occupancy.pgm"
    image_path.write_bytes(f"P5\n{d.width} {d.height}\n255\n".encode("ascii") + image.tobytes())
    yaml_path = directory / "nav_map.yaml"
    yaml_path.write_text(
        f"image: nav_occupancy.pgm\nmode: trinary\nresolution: 4.0\n"
        f"origin: [{d.bounds.left:.9f}, {d.bounds.bottom:.9f}, 0.0]\n"
        "negate: 0\noccupied_thresh: 0.65\nfree_thresh: 0.196\n", encoding="ascii")
    return {"image": image_path.name, "yaml": yaml_path.name, "resolution_m": 4.0,
            "origin_map_m": [d.bounds.left, d.bounds.bottom, 0.0], "frame": "map",
            "status": "DERIVED", "threshold_status": "SCENARIO", "slope_threshold_deg": threshold,
            "method": "3x3-supported central finite-difference slope; invalid and edge stencils occupied",
            "free_cells": int(free.sum()), "occupied_cells": int((~free).sum()),
            "image_sha256": sha256(image_path), "yaml_sha256": sha256(yaml_path)}, free


def choose_smoke_route(fine: Surface, coarse: Surface, free: np.ndarray, ops: tuple, distance: float) -> dict:
    """Choose a measured flat straight segment, not a navigation planner."""
    west, south, east, north = ops
    xs, ys = axis(west, east, 1), axis(south, north, 1)
    xx, yy = np.meshgrid(xs, ys)
    z, valid = fine.sample(xx, yy)
    slopes, supported = slope_degrees(z, valid, 1.0)
    flat = full_window_true(supported & (slopes < 3.0), 5)
    rr, cc = np.nonzero(flat)
    order = np.argsort(xx[rr, cc] ** 2 + yy[rr, cc] ** 2, kind="stable")
    d = coarse.dataset

    def nav_free(x: np.ndarray, y: np.ndarray) -> bool:
        cols = np.floor((x - d.transform.c) / 4).astype(int)
        rows = np.floor((d.transform.f - y) / 4).astype(int)
        inside = (cols >= 0) & (cols < d.width) & (rows >= 0) & (rows < d.height)
        return bool(inside.all() and free[rows, cols].all())

    for selected in order[:10000]:
        r, c = rr[selected], cc[selected]
        x0, y0 = xx[r, c], yy[r, c]
        for heading in np.arange(8) * math.pi / 4:
            along = np.linspace(0, distance, max(3, math.ceil(distance * 2) + 1))
            x, y = x0 + along * math.cos(heading), y0 + along * math.sin(heading)
            ix, iy = np.rint(x - west).astype(int), np.rint(y - south).astype(int)
            if ((ix < 0) | (ix >= len(xs)) | (iy < 0) | (iy >= len(ys))).any():
                continue
            if not flat[iy, ix].all() or not nav_free(x, y):
                continue
            heights, height_valid = fine.sample(x[[0, -1]], y[[0, -1]])
            if not height_valid.all():
                continue
            return {"status": "SCENARIO", "frame": "map", "units": "m",
                    "selection": "Nearest-origin supported 5x5 patch below 3deg; straight route entirely flat and map-free",
                    "distance_m": distance, "flat_patch_side_cells": 5,
                    "max_fine_slope_deg": float(slopes[iy, ix].max()),
                    "slope_limit_deg": 3.0,
                    "spawn": {"map_x_m": float(x0), "map_y_m": float(y0), "ground_z_m": float(heights[0]), "yaw_rad": float(heading)},
                    "goal": {"map_x_m": float(x[-1]), "map_y_m": float(y[-1]), "ground_z_m": float(heights[1]), "yaw_rad": float(heading)},
                    "rover_spawn_clearance_m": 0.6,
                    "clearance_status": "SCENARIO; root rover model must verify wheel/ground clearance"}
    raise ValueError("No supported 5x5 <3deg flat patch with a map-free smoke-test segment")


def triangle_height(fine: Surface, x: float, y: float, ops: tuple) -> float:
    west, south, _, _ = ops
    x0, y0 = west + math.floor(x-west), south + math.floor(y-south)
    xs = np.array([x0, x0+1, x0, x0+1])
    ys = np.array([y0, y0, y0+1, y0+1])
    z, valid = fine.sample(xs, ys)
    if not valid.all():
        raise ValueError("Unsupported mesh QA point")
    # OBJ local Z is rounded to six decimals. Absolute reconstruction adds
    # its origin; error <=0.5e-6m is included separately in QA's bound.
    u, v = x-x0, y-y0
    return float(z[0]*(1-u-v) + z[1]*u + z[2]*v if u+v <= 1 else
                 z[1]*(1-v) + z[2]*(1-u) + z[3]*(u+v-1))


def export_terrain(dem1m: Path, dem4m: Path, out: Path, *, ops_size: float = 1000,
                   tile_size: float = 250, goal_distance_m: float = 10,
                   slope_threshold_deg: float = 20, max_source_pixels: int = 10_000_000,
                   max_triangles: int = 4_000_000) -> dict:
    if not all(math.isfinite(v) and v > 0 for v in (ops_size, tile_size, goal_distance_m, slope_threshold_deg)):
        raise ValueError("Sizes and scenario thresholds must be finite and positive")
    if not math.isclose(ops_size/tile_size, round(ops_size/tile_size)) or not math.isclose(tile_size, round(tile_size)):
        raise ValueError("Ops size must contain whole integer-metre tiles")
    if slope_threshold_deg >= 90 or max_source_pixels < 1 or max_triangles < 1:
        raise ValueError("Invalid export limits")
    fine = Surface.open(Path(dem1m), 1.0, max_source_pixels)
    coarse = None
    try:
        coarse = Surface.open(Path(dem4m), 4.0, max_source_pixels)
        if fine.metadata["origin"] != coarse.metadata["origin"]:
            raise ValueError("Fine and coarse rasters use different map origins/H0")
        for key in ("center_lat", "center_lon_east", "expected"):
            if fine.metadata.get("identity", {}).get(key) != coarse.metadata.get("identity", {}).get(key):
                raise ValueError("Fine and coarse source coordinate identities disagree")
        if not np.allclose(fine.dataset.bounds, coarse.dataset.bounds, rtol=0, atol=1e-8):
            raise ValueError("Fine/coarse footprint bounds must match")
        outer = fine.domain
        half = ops_size / 2
        ops = (-half, -half, half, half)
        if not (outer[0] < -half and outer[1] < -half and outer[2] > half and outer[3] > half):
            raise ValueError("Ops box must be strictly within the DEM pixel-centre domain")
        estimated = 2*ops_size**2 + 2*(outer[2]-outer[0])*(outer[3]-outer[1])/16 + 40*ops_size
        if estimated > max_triangles:
            raise ValueError("Conservative triangle budget exceeded before allocation")
        identity = {"algorithm": ALGORITHM, "helper_sha256": sha256(Path(__file__)),
                    "fine_sha256": fine.digest, "coarse_sha256": coarse.digest,
                    "fine_sidecar_sha256": fine.sidecar_digest, "coarse_sidecar_sha256": coarse.sidecar_digest,
                    "ops_size_m": ops_size, "tile_size_m": tile_size, "goal_distance_m": goal_distance_m,
                    "slope_threshold_deg": slope_threshold_deg, "max_source_pixels": max_source_pixels,
                    "max_triangles": max_triangles, "engine_z_offset_m": 0.0}
        out = Path(out)
        manifest_path = out / "manifest.json"
        if out.exists():
            if not manifest_path.is_file():
                raise FileExistsError("Output exists without a complete manifest; use a new output path")
            cached = json.loads(manifest_path.read_text(encoding="utf-8"))
            if cached.get("identity") != identity:
                raise FileExistsError("Output belongs to a different source/configuration; use a new output path")
            for item in cached["artifacts"]:
                candidate = (out / item["relative_path"]).resolve()
                if candidate.parent != out.resolve() or sha256(candidate) != item["sha256"]:
                    raise ValueError("Cached terrain artifact hash mismatch")
            return {**cached, "cache_hit": True}
        out.parent.mkdir(parents=True, exist_ok=True)
        centre_z, centre_valid = fine.sample(np.array([0.0]), np.array([0.0]))
        if not centre_valid[0]:
            raise ValueError("Map centre has no supported elevation")
        origin_z = float(centre_z[0])
        with tempfile.TemporaryDirectory(prefix=out.name + ".partial-", dir=out.parent) as temp:
            directory = Path(temp) / "complete"
            directory.mkdir()
            meshes, artifacts = [], []
            tile_count = round(ops_size / tile_size)
            for row in range(tile_count):
                for col in range(tile_count):
                    bounds = (-half+col*tile_size, -half+row*tile_size,
                              -half+(col+1)*tile_size, -half+(row+1)*tile_size)
                    vertices, faces = ops_mesh(fine, bounds)
                    origin = np.array([(bounds[0]+bounds[2])/2, (bounds[1]+bounds[3])/2, origin_z])
                    mesh = write_obj(directory/f"ops_{row:02d}_{col:02d}.obj", vertices, faces, origin)
                    mesh.update(id=f"ops_{row:02d}_{col:02d}", role="ops_1m", requested_bounds_map_m=list(bounds))
                    meshes.append(mesh)
            chunks, face_chunks, details, offset = [], [], [], 0
            for name in ("north", "south", "west", "east"):
                vertices, faces, detail = ring_patch(fine, coarse, name, outer, ops)
                chunks.append(vertices)
                face_chunks.append(faces + offset)
                details.append(detail)
                offset += len(vertices)
            mesh = write_obj(directory/"coarse_ring.obj", np.concatenate(chunks), np.concatenate(face_chunks), np.array([0, 0, origin_z]))
            mesh.update(id="coarse_ring", role="surround_4m", patches=details, inner_hole_bounds_map_m=list(ops))
            meshes.append(mesh)
            if sum(m["triangles"] for m in meshes) > max_triangles:
                raise ValueError("Actual triangle budget exceeded")
            nav, free = nav_map(coarse, directory, slope_threshold_deg)
            route = choose_smoke_route(fine, coarse, free, ops, goal_distance_m)
            controls = []
            for i, (fx, fy) in enumerate(((0.1913, 0.3817), (0.5311, 0.7163), (0.8179, 0.2693)), 1):
                x, y = -half + fx*ops_size, -half + fy*ops_size
                expected, valid = fine.sample(np.array([x]), np.array([y]))
                mesh_z = triangle_height(fine, x, y, ops)
                error = abs(mesh_z-float(expected[0])) + 0.000001
                controls.append({"id": f"P{i}", "map_x_m": x, "map_y_m": y,
                                 "dem_bilinear_z_m": float(expected[0]), "mesh_triangle_z_m": mesh_z,
                                 "error_bound_m": error, "passed": bool(valid[0] and error <= 0.1)})
            for path in sorted(directory.iterdir()):
                artifacts.append({"relative_path": path.name, "sha256": sha256(path), "bytes": path.stat().st_size})
            manifest = {"schema_version": 1, "identity": identity, "status": "DERIVED",
                        "created_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                        "frame": "map", "units": "m", "map_origin": fine.metadata["origin"],
                        "engine_z_offset_m": 0.0,
                        "height_contract": "OBJ local z + mesh pose z equals existing map z=source H-H0; no new datum or engine height offset",
                        "sources": {"dem1m": fine.info(), "dem4m": coarse.info()},
                        "raster_footprint_bounds_map_m": list(fine.dataset.bounds),
                        "mesh_support_bounds_map_m": list(outer), "ops_bounds_map_m": list(ops),
                        "mesh_sampling": "1m ops; 4m ring; shared ops edges use 1m source; outer support edge uses 1m source; no extrapolation",
                        "meshes": meshes, "nav": nav, "scenario": route,
                        "spawn": route["spawn"], "goal": route["goal"],
                        "qa": {"three_point_test": controls, "three_point_passed": all(c["passed"] for c in controls),
                               "tolerance_m": 0.1, "serialization_error_allowance_m": 0.000001,
                               "visual_collision_same_artifact": True,
                               "topology": "Partition: 16 default ops tiles and four joined ring patches; zero-area shared edges, no coplanar face overlap",
                               "independent_ground_alignment_verified": False},
                        "budgets": {"max_source_pixels": max_source_pixels, "max_triangles": max_triangles,
                                    "triangles": sum(m["triangles"] for m in meshes),
                                    "vertices": sum(m["vertices"] for m in meshes)},
                        "artifacts": artifacts, "cache_hit": False,
                        "limits": ["Slope occupancy and smoke-test route are SCENARIO settings, not a T2 mission planner.",
                                   "The centre-sample domain is smaller than the raster footprint by half a pixel at each outside edge.",
                                   "No rendered Gazebo contact/line-trace test is claimed by this export helper."]}
            (directory/"manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False)+"\n", encoding="utf-8")
            os.rename(directory, out)
        return manifest
    finally:
        fine.dataset.close()
        if coarse is not None:
            coarse.dataset.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dem1m", required=True, type=Path)
    parser.add_argument("--dem4m", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--ops-size", type=float, default=1000)
    parser.add_argument("--tile-size", type=float, default=250)
    parser.add_argument("--goal-distance-m", type=float, default=10)
    parser.add_argument("--slope-threshold-deg", type=float, default=20)
    parser.add_argument("--max-source-pixels", type=int, default=10_000_000)
    parser.add_argument("--max-triangles", type=int, default=4_000_000)
    args = parser.parse_args()
    result = export_terrain(args.dem1m, args.dem4m, args.out, ops_size=args.ops_size,
                            tile_size=args.tile_size, goal_distance_m=args.goal_distance_m,
                            slope_threshold_deg=args.slope_threshold_deg,
                            max_source_pixels=args.max_source_pixels, max_triangles=args.max_triangles)
    print(json.dumps({"manifest": (args.out/"manifest.json").as_posix(), "cache_hit": result["cache_hit"],
                      "meshes": len(result["meshes"]), "triangles": result["budgets"]["triangles"],
                      "three_point_passed": result["qa"]["three_point_passed"],
                      "spawn": result["spawn"], "goal": result["goal"]}, indent=2))


if __name__ == "__main__":
    main()
