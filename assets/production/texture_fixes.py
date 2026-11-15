"""Texture revisions on derived packages (originals in source.glb / source folders stay intact).

habitat: removes NASA insignia, US flags, the "HAB X" logo and the HDU emblems from the
derived base-colour sheet. The visual guide forbids NASA brand elements in REDLINE content
and NASA's media guidelines restrict insignia use; generic "Segment"/"AIRLOCK" signage stays.
sample_case: recolours the blue Earth warehouse tote to the project's light-grey palette,
keeping wear detail and the white labels.
Usage (Python with OpenCV): python texture_fixes.py
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_SHA = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read(path: Path) -> np.ndarray:
    return cv2.imdecode(np.frombuffer(path.read_bytes(), np.uint8), cv2.IMREAD_UNCHANGED)


def encode(image: np.ndarray) -> bytes:
    ok, data = cv2.imencode(".png", image)
    if not ok:
        raise SystemExit("PNG encoding failed")
    return data.tobytes()


def original_bytes(path: Path) -> bytes:
    """Refuse to edit anything but the delivered texture recorded in MANIFEST.json (no double edits)."""
    manifest = {f["path"]: f["sha256"] for f in json.loads((ROOT / "MANIFEST.json").read_text(encoding="utf-8"))["files"]}
    data = path.read_bytes()
    if manifest.get(path.relative_to(ROOT).as_posix()) != sha256(data):
        raise SystemExit(f"{path.name} is not the original delivered texture; restore it before re-running")
    return data


def copies(folder: Path, name: str) -> list[Path]:
    """The base texture plus the copies Blender's FBX export placed in each .fbm folder."""
    return [folder / "textures" / name, *sorted(folder.glob(f"unreal/*.fbm/{name}"))]


# (x0, y0, x1, y1, min saturation): pale small flags and the thin green caption need lower
# thresholds. V > 0.35 keeps the dark navy portholes out of every mask.
LOGO_REGIONS = ((0, 0, 480, 660, 0.35), (125, 0, 157, 660, 0.12), (180, 0, 276, 660, 0.10))


def saturated_components(bgr: np.ndarray, regions=LOGO_REGIONS) -> tuple[np.ndarray, int]:
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    sat = np.zeros(bgr.shape[:2], np.uint8)
    for x0, y0, x1, y1, smin in regions:
        region = (hsv[y0:y1, x0:x1, 1] > smin * 255) & (hsv[y0:y1, x0:x1, 2] > 0.35 * 255)
        sat[y0:y1, x0:x1] |= region.astype(np.uint8)
    count, _, stats, _ = cv2.connectedComponentsWithStats(sat, connectivity=8)
    mask = np.zeros_like(sat)
    kept = 0
    for i in range(1, count):
        x, y, w, h, area = stats[i]
        if area < 3:
            continue
        kept += 1
        mask[max(0, y - 3):y + h + 3, max(0, x - 3):x + w + 3] = 255  # include white parts inside a logo
    return mask, kept


EMBLEM_WINDOWS = ((34, 232, 92, 288), (62, 555, 124, 610))


def habitat() -> dict:
    folder = ROOT / "incoming/habitat"
    paths = copies(folder, "HDU_01.png")
    original = original_bytes(paths[0])
    image = read(paths[0])
    bgr, alpha = image[..., :3].copy(), (image[..., 3] if image.shape[2] == 4 else None)
    # Regions cover the hull segment strip and decal column; door art and the pale zig-zag are outside.
    mask, logos = saturated_components(bgr)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    # Protect the portholes: large dark blobs plus a 7 px rim stay out of the logo mask.
    dark = (hsv[..., 2] < 0.3 * 255).astype(np.uint8)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(dark, connectivity=8)
    blobs = np.isin(labels, [i for i in range(1, count) if stats[i, cv2.CC_STAT_AREA] >= 150]).astype(np.uint8)
    protect = cv2.dilate(blobs, np.ones((15, 15), np.uint8)) > 0
    mask[protect] = 0
    for x0, y0, x1, y1 in EMBLEM_WINDOWS:  # black/white HDU emblems (porthole starts at x = 97)
        window = (hsv[y0:y1, x0:x1, 2] < 0.72 * 255) | (hsv[y0:y1, x0:x1, 1] > 0.12 * 255)
        grown = cv2.dilate(window.astype(np.uint8) * 255, np.ones((5, 5), np.uint8))
        mask[y0:y1, x0:x1] = np.maximum(mask[y0:y1, x0:x1], grown)
    cleaned = cv2.inpaint(bgr, mask, 4, cv2.INPAINT_TELEA)
    leftover, remaining = saturated_components(cleaned)
    # Warm porthole rims are deliberately kept; only leftovers outside them would be logo remnants.
    _, outside = cv2.connectedComponents(((leftover > 0) & ~protect).astype(np.uint8), connectivity=8)
    result = np.dstack([cleaned, alpha]) if alpha is not None else cleaned
    data = encode(result)
    for path in paths:
        path.write_bytes(data)
    return {"texture": "HDU_01.png", "files": [p.relative_to(ROOT).as_posix() for p in paths],
            "sha256_before": sha256(original), "sha256_after": sha256(data),
            "saturated_logo_components_removed": logos, "saturated_components_remaining_total": remaining,
            "saturated_components_remaining_outside_porthole_protection": int(outside.max()),
            "porthole_protection": "dark blobs (V < 0.3, area >= 150 px) dilated 7 px are never masked",
            "logo_regions_px_min_saturation": [list(r) for r in LOGO_REGIONS],
            "hdu_emblem_windows_px": [list(w) for w in EMBLEM_WINDOWS],
            "masked_pixels": int((mask > 0).sum()), "method": "OpenCV Telea inpaint, radius 4 px",
            "kept": "generic 'Segment A-H' and 'AIRLOCK' signage, door art, porthole"}


def sample_case() -> dict:
    folder = ROOT / "incoming/sample_case"
    paths = copies(folder, "industrial_pastic_container_diff.png")
    original = original_bytes(paths[0])
    image = read(paths[0])
    bgr = image[..., :3].astype(np.float32)
    hsv = cv2.cvtColor(image[..., :3], cv2.COLOR_BGR2HSV)
    blue = (hsv[..., 0] >= 95) & (hsv[..., 0] <= 135) & (hsv[..., 1] > 0.25 * 255)
    value = hsv[..., 2].astype(np.float32)
    reference = float(np.median(value[blue]))
    target = np.array([200.0, 205.0, 205.0], np.float32)  # BGR light grey (sRGB ~ #CDCDC8)
    recolored = np.clip(target[None, None, :] * (value / reference)[..., None], 0, 255)
    bgr[blue] = recolored[blue]
    result = bgr.astype(np.uint8)
    if image.shape[2] == 4:
        result = np.dstack([result, image[..., 3]])
    data = encode(result)
    for path in paths:
        path.write_bytes(data)
    return {"texture": "industrial_pastic_container_diff.png", "files": [p.relative_to(ROOT).as_posix() for p in paths],
            "sha256_before": sha256(original), "sha256_after": sha256(data),
            "recoloured_pixel_fraction": float(blue.mean()), "reference_value": reference,
            "method": "blue-hue pixels -> light grey scaled by their value; labels and wear kept"}


if __name__ == "__main__":
    report = {"created_utc": datetime.now(timezone.utc).isoformat(), "script_sha256": SCRIPT_SHA,
              "opencv": cv2.__version__, "habitat": habitat(), "sample_case": sample_case()}
    (ROOT / "production/texture_fixes.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=1))
