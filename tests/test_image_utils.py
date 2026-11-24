"""Tests for image loading, geometry, colour and JSON helpers."""

from __future__ import annotations

import hashlib

import pytest
from PIL import Image

from sprite_studio.image_utils import (
    alpha_bbox,
    alpha_stats,
    anchor_offset,
    checkerboard,
    fit_preview,
    flatten_on,
    integer_scale,
    natural_key,
    pad_to_canvas,
    palette,
    parse_color,
    read_json,
    resize_to_fit,
    save_png,
    sha256_file,
    trim,
    write_json,
)


def test_alpha_bbox_and_stats(frame):
    assert alpha_bbox(frame) == (4, 4, 11, 11)
    stats = alpha_stats(frame)
    assert stats["bbox"] == [4, 4, 11, 11]
    assert stats["opaque_pixels"] == 64
    assert stats["transparent_pixels"] == 256 - 64
    assert stats["coverage"] == pytest.approx(0.25)


def test_empty_image_has_no_bbox():
    assert alpha_bbox(Image.new("RGBA", (8, 8), (0, 0, 0, 0))) is None


def test_trim_respects_padding(frame):
    trimmed, bbox = trim(frame, padding=1)
    assert bbox == (4, 4, 11, 11)
    assert trimmed.size == (10, 10)


def test_pad_and_anchor_offsets(frame):
    canvas = pad_to_canvas(frame, 24, 24, anchor="bottom-center")
    assert canvas.size == (24, 24)
    assert alpha_bbox(canvas) == (8, 12, 15, 19)
    assert anchor_offset((16, 16), (24, 24), "top-left") == (0, 0)
    assert anchor_offset((16, 16), (24, 24), "bottom-right") == (8, 8)
    with pytest.raises(ValueError):
        pad_to_canvas(frame, 8, 8)


def test_resize_to_fit_does_not_upscale(frame):
    assert resize_to_fit(frame, 64, 64).size == (16, 16)
    assert resize_to_fit(frame, 64, 64, allow_upscale=True).size == (64, 64)
    assert integer_scale(frame, 3).size == (48, 48)


def test_palette_ignores_transparent_rgb(frame):
    image = frame.copy()
    # Hidden RGB under alpha=0 must not appear in the extracted palette.
    image.putpixel((0, 0), (255, 0, 255, 0))
    colours = {entry["hex"] for entry in palette(image, max_colors=8)}
    assert "#ff00ff" not in colours


def test_checkerboard_and_preview():
    board = checkerboard(8, 8, size=4)
    assert board.size == (8, 8)
    preview = fit_preview(Image.new("RGBA", (4, 4), (255, 0, 0, 255)), (16, 16))
    assert preview.size == (16, 16)
    assert preview.mode == "RGBA"


def test_parse_colour_formats():
    assert parse_color("#abc") == (170, 187, 204, 255)
    assert parse_color("#11223344") == (17, 34, 51, 68)
    assert parse_color((1, 2, 3)) == (1, 2, 3, 255)
    with pytest.raises(ValueError):
        parse_color("not-a-colour")


def test_flatten_on_composites_alpha(frame):
    flat = flatten_on(frame, (255, 255, 255, 255))
    assert flat.getpixel((0, 0)) == (255, 255, 255, 255)
    assert flat.getpixel((4, 4)) == (80, 140, 90, 255)


def test_save_png_refuses_accidental_overwrite(tmp_path, frame):
    target = tmp_path / "frame.png"
    save_png(frame, target)
    assert target.is_file()
    with pytest.raises(FileExistsError):
        save_png(frame, target)
    save_png(frame, target, overwrite=True)
    assert target.is_file()


def test_json_roundtrip_and_hash(tmp_path):
    data = {"asset_id": "demo", "values": [1, 2, 3]}
    path = tmp_path / "data.json"
    write_json(path, data)
    assert read_json(path) == data
    expected = hashlib.sha256(path.read_bytes()).hexdigest()
    assert sha256_file(path) == expected


def test_natural_key_orders_frames():
    names = ["frame_10.png", "frame_2.png", "frame_1.png"]
    assert sorted(names, key=natural_key) == ["frame_1.png", "frame_2.png", "frame_10.png"]
