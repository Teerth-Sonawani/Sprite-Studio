"""Sprite-sheet slicing, assembly, contact-sheet and tile tests."""

from __future__ import annotations

import pytest
from PIL import Image, ImageDraw

from sprite_studio.sheets import build_sheet, contact_sheet, find_frames, slice_sheet
from sprite_studio.tiling import assembled_preview, seam_report, wrap_preview


def _cells() -> list[Image.Image]:
    cells = []
    for index in range(4):
        image = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
        ImageDraw.Draw(image).rectangle((index, 1, index + 3, 6), fill=(index * 40, 120, 90, 255))
        cells.append(image)
    return cells


def test_build_horizontal_sheet_and_metadata():
    frames = _cells()
    sheet, meta = build_sheet(frames, layout="horizontal", cell_width=8, cell_height=8, durations=[100] * 4)
    assert sheet.size == (32, 8)
    assert meta["frame_count"] == 4
    assert meta["sheet"]["columns"] == 4
    assert meta["sheet"]["rows"] == 1
    assert [frame["duration_ms"] for frame in meta["frames"]] == [100] * 4


def test_build_grid_and_vertical_layouts():
    frames = _cells()
    grid, meta = build_sheet(frames, layout="grid", columns=2, cell_width=8, cell_height=8)
    assert grid.size == (16, 16)
    assert (meta["sheet"]["columns"], meta["sheet"]["rows"]) == (2, 2)
    vertical, vmeta = build_sheet(frames, layout="vertical", cell_width=8, cell_height=8)
    assert vertical.size == (8, 32)
    assert (vmeta["sheet"]["columns"], vmeta["sheet"]["rows"]) == (1, 4)


def test_build_sheet_rejects_oversized_cells():
    with pytest.raises(ValueError):
        build_sheet([Image.new("RGBA", (16, 16))], cell_width=8, cell_height=8)


def test_slice_sheet_roundtrip_and_skip_empty(tmp_path):
    sheet, _ = build_sheet(_cells(), layout="grid", columns=2, cell_width=8, cell_height=8)
    metadata = slice_sheet(sheet, columns=2, rows=2, cell_width=8, cell_height=8, out_dir=tmp_path)
    assert metadata["frame_count"] == 4
    assert len(list(tmp_path.glob("*.png"))) == 4
    assert metadata["frames"][0]["column"] == 0
    assert metadata["frames"][3]["row"] == 1

    empty = Image.new("RGBA", (16, 8), (0, 0, 0, 0))
    empty.paste(_cells()[0], (0, 0))
    empty_meta = slice_sheet(
        empty, columns=2, rows=1, cell_width=8, cell_height=8, out_dir=tmp_path / "empty"
    )
    assert empty_meta["empty_cell_count"] == 1
    assert empty_meta["frame_count"] == 1


def test_slice_sheet_requires_grid_definition():
    with pytest.raises(ValueError):
        slice_sheet(Image.new("RGBA", (8, 8)))


def test_contact_sheet_and_find_frames(tmp_path):
    frames = _cells()
    sheet = contact_sheet(frames, columns=2, title="demo")
    assert sheet.mode == "RGBA"
    assert sheet.width > 0 and sheet.height > 0
    for index, frame in enumerate(frames):
        frame.save(tmp_path / f"frame_{index + 1}.png")
    found = find_frames(tmp_path)
    assert [path.name for path in found] == [f"frame_{index}.png" for index in range(1, 5)]


def test_seam_report_passes_on_wrapped_pattern():
    tile = Image.new("RGBA", (16, 16), (60, 110, 80, 255))
    draw = ImageDraw.Draw(tile)
    for x in range(0, 16, 4):
        draw.line((x, 0, x, 15), fill=(90, 150, 100, 255))
    # Dense interior detail legitimately makes the boundary ratio noisy; the
    # absolute difference is still below the configured ceiling.
    report = seam_report(tile)
    assert report["status"] == "PASS"
    assert report["axes"]["x"]["passes_absolute"] is True


def test_seam_report_warns_on_high_contrast_boundary():
    tile = Image.new("RGBA", (16, 16), (0, 0, 0, 255))
    ImageDraw.Draw(tile).rectangle((8, 0, 15, 15), fill=(255, 255, 255, 255))
    report = seam_report(tile, threshold=2.0, max_edge_diff=48)
    assert report["status"] == "WARN"


def test_wrap_and_assembled_previews():
    tile = Image.new("RGBA", (8, 8), (40, 80, 60, 255))
    assert wrap_preview(tile, 2).size == (16, 16)
    assembled = assembled_preview(tile, grid=3)
    assert assembled.size == (24, 24)
    assert assembled.mode == "RGBA"
