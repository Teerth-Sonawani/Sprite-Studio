"""Shelf atlas packing and file-based packing tests."""

from __future__ import annotations

import pytest
from PIL import Image

from sprite_studio.atlas import pack_atlas, pack_files


def _item(name: str, width: int, height: int) -> dict:
    image = Image.new("RGBA", (width, height), (40, 90, 60, 255))
    return {"name": name, "image": image, "pivot": {"x": width // 2, "y": height}}


def _overlaps(a: dict, b: dict) -> bool:
    return not (
        a["x"] + a["w"] <= b["x"]
        or b["x"] + b["w"] <= a["x"]
        or a["y"] + a["h"] <= b["y"]
        or b["y"] + b["h"] <= a["y"]
    )


def test_pack_atlas_places_all_items_without_overlap():
    items = [_item("a", 10, 10), _item("b", 8, 12), _item("c", 12, 8)]
    sheet, meta = pack_atlas(items, max_width=64, max_height=64, padding=2)
    assert meta["frame_count"] == 3
    assert sheet.width <= 64 and sheet.height <= 64
    for index, first in enumerate(meta["frames"]):
        assert first["x"] >= 2 and first["y"] >= 2
        assert first["x"] + first["w"] <= sheet.width
        assert first["y"] + first["h"] <= sheet.height
        for second in meta["frames"][index + 1 :]:
            assert not _overlaps(first, second)


def test_pack_atlas_power_of_two_dimensions():
    _, meta = pack_atlas([_item("a", 10, 10), _item("b", 10, 10)], power_of_two=True)
    width = meta["image"]["width"]
    height = meta["image"]["height"]
    assert width & (width - 1) == 0
    assert height & (height - 1) == 0


def test_pack_atlas_rejects_oversized_item():
    with pytest.raises(ValueError):
        pack_atlas([_item("wide", 100, 10)], max_width=32, max_height=32)


def test_pack_atlas_rejects_empty_and_bad_sort():
    with pytest.raises(ValueError):
        pack_atlas([])
    with pytest.raises(ValueError):
        pack_atlas([_item("a", 8, 8)], sort="magic")


def test_pack_files_writes_sheet_and_metadata(tmp_path):
    paths = []
    for index in range(3):
        path = tmp_path / f"item_{index}.png"
        _item(f"item_{index}", 8, 8)["image"].save(path)
        paths.append(path)
    output = tmp_path / "atlas.png"
    metadata = tmp_path / "atlas.json"
    meta = pack_files(paths, output, metadata_path=metadata, padding=1)
    assert output.is_file()
    assert metadata.is_file()
    assert meta["frame_count"] == 3
