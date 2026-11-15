"""Exact textures for procedural REDLINE props (run with any Python that has OpenCV).

ArUco markers must be the dictionary's exact bit pattern; a generative model cannot
be trusted with them. Each marker is re-detected from the written PNG as evidence.
Usage: python make_textures.py
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DICTIONARY = "DICT_4X4_50"
MARKER_IDS = (10, 11)
CELLS = 6  # 4x4 data bits + 1-cell black border on each side
CELL_PX = 80
MARKER_SIZE_M = 0.15
QUIET_CELLS = 1  # white margin of one cell around the black border


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# cv2.imwrite/imread fail on non-ASCII Windows paths (this checkout has "İ").
def write_png(path: Path, image: np.ndarray) -> None:
    ok, data = cv2.imencode(".png", image)
    if not ok:
        raise SystemExit(f"PNG encoding failed for {path.name}")
    path.write_bytes(data.tobytes())


def read_gray(path: Path) -> np.ndarray:
    return cv2.imdecode(np.frombuffer(path.read_bytes(), dtype=np.uint8), cv2.IMREAD_GRAYSCALE)


def aruco_textures() -> dict:
    out = ROOT / "incoming/valve_panel/textures_src"
    out.mkdir(parents=True, exist_ok=True)
    dictionary = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, DICTIONARY))
    detector = cv2.aruco.ArucoDetector(dictionary, cv2.aruco.DetectorParameters())
    records = []
    for marker_id in MARKER_IDS:
        marker = cv2.aruco.generateImageMarker(dictionary, marker_id, CELLS * CELL_PX)
        image = cv2.copyMakeBorder(marker, *(4 * [QUIET_CELLS * CELL_PX]), cv2.BORDER_CONSTANT, value=255)
        path = out / f"aruco_{marker_id}.png"
        write_png(path, image)
        reread = read_gray(path)
        _, ids, _ = detector.detectMarkers(reread)
        detected = sorted(int(i) for i in ids.ravel()) if ids is not None else []
        if detected != [marker_id]:
            raise SystemExit(f"marker {marker_id} re-detection failed: {detected}")
        records.append({"id": marker_id, "png": path.relative_to(ROOT).as_posix(), "sha256": sha256(path),
                        "pixels": image.shape[0], "redetected_ids": detected})
    plate_m = MARKER_SIZE_M * (CELLS + 2 * QUIET_CELLS) / CELLS
    return {"dictionary": DICTIONARY, "marker_size_m": MARKER_SIZE_M, "plate_size_m": plate_m,
            "cell_size_m": MARKER_SIZE_M / CELLS, "quiet_zone_cells": QUIET_CELLS,
            "opencv": cv2.__version__, "markers": records}


def drone_pad_texture() -> dict:
    out = ROOT / "incoming/drone_pad/textures_src"
    out.mkdir(parents=True, exist_ok=True)
    size = 1024
    c = size // 2
    image = np.full((size, size, 3), (23, 21, 20), dtype=np.uint8)  # BGR graphite
    white, red = (235, 235, 235), (40, 40, 200)
    cv2.circle(image, (c, c), int(0.93 * c), white, 18, cv2.LINE_AA)
    cv2.circle(image, (c, c), int(0.36 * c), white, 10, cv2.LINE_AA)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        start = (int(c + dx * 0.42 * c), int(c + dy * 0.42 * c))
        end = (int(c + dx * 0.84 * c), int(c + dy * 0.84 * c))
        cv2.line(image, start, end, white, 9, cv2.LINE_AA)
    # Heading mark toward image +v (texture "north"); documents the pad's yaw.
    tip = (c, int(0.06 * c))
    cv2.fillPoly(image, [np.array([tip, (c - 34, int(0.2 * c)), (c + 34, int(0.2 * c))])], red, cv2.LINE_AA)
    path = out / "drone_pad_markings.png"
    write_png(path, image)
    return {"png": path.relative_to(ROOT).as_posix(), "sha256": sha256(path), "pixels": size,
            "content": "graphite field, outer/inner rings, crosshair, red heading mark toward texture +v"}


if __name__ == "__main__":
    report = {"aruco": aruco_textures(), "drone_pad": drone_pad_texture()}
    (ROOT / "production/procedural_textures.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=1))
