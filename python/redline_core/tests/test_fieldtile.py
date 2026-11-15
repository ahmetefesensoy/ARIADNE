import io
import struct
import zlib

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from redline_core.fieldtile import decode_tile, encode_tile


def png_header(png: bytes) -> dict:
    """Independent IHDR reader (does not use Pillow)."""
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    length, kind = struct.unpack(">I4s", png[8:16])
    assert kind == b"IHDR" and length == 13
    width, height, depth, color, _, _, interlace = struct.unpack(">IIBBBBB", png[16:29])
    return {"width": width, "height": height, "bit_depth": depth, "color_type": color, "interlace": interlace}


def raw_rows(png: bytes, width: int, height: int, bytes_per_sample: int) -> np.ndarray:
    """Independent PNG decoder for unfiltered-or-filtered greyscale, non-interlaced images."""
    pos, data = 8, b""
    while pos < len(png):
        length, kind = struct.unpack(">I4s", png[pos:pos + 8])
        if kind == b"IDAT":
            data += png[pos + 8:pos + 8 + length]
        pos += 12 + length
    raw = zlib.decompress(data)
    stride = width * bytes_per_sample
    out = np.zeros((height, stride), dtype=np.int64)
    prev = np.zeros(stride, dtype=np.int64)
    for r in range(height):
        f = raw[r * (stride + 1)]
        line = np.frombuffer(raw[r * (stride + 1) + 1:(r + 1) * (stride + 1)], dtype=np.uint8).astype(np.int64)
        cur = np.zeros(stride, dtype=np.int64)
        for i in range(stride):
            left = cur[i - bytes_per_sample] if i >= bytes_per_sample else 0
            up = prev[i]
            ul = prev[i - bytes_per_sample] if i >= bytes_per_sample else 0
            if f == 0:
                pred = 0
            elif f == 1:
                pred = left
            elif f == 2:
                pred = up
            elif f == 3:
                pred = (left + up) // 2
            else:
                p = left + up - ul
                pa, pb, pc = abs(p - left), abs(p - up), abs(p - ul)
                pred = left if pa <= pb and pa <= pc else (up if pb <= pc else ul)
            cur[i] = (line[i] + pred) & 0xFF
        out[r] = cur
        prev = cur
    if bytes_per_sample == 2:
        return out[:, 0::2] * 256 + out[:, 1::2]
    return out


def test_png_is_north_up_greyscale_with_expected_depth():
    grid = np.arange(12, dtype=float).reshape(3, 4)  # row 0 = south
    for depth, sample_bytes in ((8, 1), (16, 2)):
        tile = encode_tile(grid, 0.0, 11.0, bit_depth=depth)
        header = png_header(tile.png)
        assert header == {"width": 4, "height": 3, "bit_depth": depth, "color_type": 0, "interlace": 0}
        codes = raw_rows(tile.png, 4, 3, sample_bytes)
        # PNG row 0 is the north row = grid row 2.
        np.testing.assert_allclose(codes * tile.scale + tile.offset, grid[::-1], atol=tile.scale / 2 + 1e-6)


def test_round_trip_error_is_at_most_half_a_step():
    rng = np.random.default_rng(3)
    grid = rng.uniform(-80.0, 320.0, size=(40, 30))
    tile = encode_tile(grid, -60.0, 300.0, bit_depth=16)
    decoded = decode_tile(tile.png, tile.scale, tile.offset, tile.nodata_byte)
    expected = np.clip(grid, -60.0, 300.0)
    assert np.max(np.abs(decoded - expected)) <= tile.scale / 2 + 1e-9


def test_nan_is_nodata_and_infinities_clamp_to_range_ends():
    grid = np.array([[np.nan, -np.inf, np.inf], [-1000.0, 0.0, 1000.0]])
    tile = encode_tile(grid, -10.0, 10.0, bit_depth=8)
    decoded = decode_tile(tile.png, tile.scale, tile.offset, tile.nodata_byte)
    assert np.isnan(decoded[0, 0])
    assert decoded[0, 1] == pytest.approx(-10.0) and decoded[1, 0] == pytest.approx(-10.0)
    assert decoded[0, 2] == pytest.approx(10.0) and decoded[1, 2] == pytest.approx(10.0)
    assert np.isnan(decoded).sum() == 1


def test_nodata_255_for_8_bit_keeps_code_zero_valid():
    grid = np.array([[0.0, np.nan], [5.0, 10.0]])
    tile = encode_tile(grid, 0.0, 10.0, bit_depth=8, nodata_byte=255)
    codes = raw_rows(tile.png, 2, 2, 1)[::-1]
    assert codes[0, 0] == 0 and codes[0, 1] == 255 and codes[1, 1] == 254
    decoded = decode_tile(tile.png, tile.scale, tile.offset, 255)
    assert decoded[0, 0] == pytest.approx(0.0) and np.isnan(decoded[0, 1])


@pytest.mark.parametrize("depth,nodata", [(16, 255), (8, 7), (12, 0)])
def test_rejects_nodata_inside_the_range_and_unknown_depth(depth, nodata):
    with pytest.raises(ValueError):
        encode_tile(np.zeros((2, 2)), 0.0, 1.0, bit_depth=depth, nodata_byte=nodata)


@pytest.mark.parametrize("lo,hi", [(1.0, 1.0), (2.0, 1.0), (0.0, np.inf), (np.nan, 1.0)])
def test_rejects_bad_ranges(lo, hi):
    with pytest.raises(ValueError):
        encode_tile(np.zeros((2, 2)), lo, hi)


def test_scale_and_offset_are_float32_exact():
    tile = encode_tile(np.zeros((2, 2)), -60.0, 300.0, bit_depth=16)
    assert np.float32(tile.scale) == tile.scale and np.float32(tile.offset) == tile.offset


@settings(max_examples=40, deadline=None)
@given(st.integers(1, 12), st.integers(1, 12), st.sampled_from([8, 16]), st.integers(0, 2**31 - 1))
def test_property_round_trip(height, width, depth, seed):
    rng = np.random.default_rng(seed)
    grid = rng.uniform(-5.0, 5.0, size=(height, width))
    grid[rng.random(grid.shape) < 0.2] = np.nan
    tile = encode_tile(grid, -4.0, 4.0, bit_depth=depth)
    decoded = decode_tile(tile.png, tile.scale, tile.offset, tile.nodata_byte)
    assert np.array_equal(np.isnan(decoded), np.isnan(grid))
    finite = ~np.isnan(grid)
    assert np.all(np.abs(decoded[finite] - np.clip(grid[finite], -4.0, 4.0)) <= tile.scale / 2 + 1e-9)


def test_bxw_sized_8_bit_margin_tile_fits_the_300_kb_budget():
    # proje.md §17: FieldTile PNG ≤ 300 KB. A 750×750 margin-like field with
    # 0.5 min noise; a full-range 16-bit tile of the same field is ~760 KB.
    y, x = np.mgrid[0:750, 0:750] * 4.0
    field = 240.0 - np.hypot(x - 1500.0, y - 1500.0) / 15.0 + 5.0 * np.sin(x / 90.0)
    field += np.random.default_rng(0).normal(0.0, 0.5, field.shape)
    field[(x - 600.0) ** 2 + (y - 2200.0) ** 2 < 300.0**2] = np.nan
    tile = encode_tile(field, -60.0, 300.0, bit_depth=8)
    assert len(tile.png) <= 300 * 1024


def test_explicit_step_quantises_on_that_step():
    grid = np.array([[0.0, 0.26], [0.74, 10.0]])
    tile = encode_tile(grid, 0.0, 10.0, bit_depth=16, step=0.5)
    assert tile.scale == 0.5 and tile.offset == -0.5
    decoded = decode_tile(tile.png, tile.scale, tile.offset, tile.nodata_byte)
    np.testing.assert_allclose(decoded, [[0.0, 0.5], [0.5, 10.0]])
    with pytest.raises(ValueError):
        encode_tile(grid, 0.0, 10.0, bit_depth=8, step=0.01)  # 1000 steps > 254 codes
    with pytest.raises(ValueError):
        encode_tile(grid, 0.0, 10.0, step=0.0)


def test_decode_rejects_colour_png():
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (2, 2)).save(buffer, format="PNG")
    with pytest.raises(ValueError):
        decode_tile(buffer.getvalue(), 1.0, 0.0, 0)
