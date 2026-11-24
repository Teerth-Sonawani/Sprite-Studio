"""Simple, deterministic shelf atlas packing."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from PIL import Image

from .image_utils import ensure_rgba, load_image, save_png, write_json


def _next_power_of_two(value: int) -> int:
    return 1 << max(0, (value - 1).bit_length())


def pack_atlas(
    items: Sequence[dict],
    max_width: int = 2048,
    max_height: int = 2048,
    padding: int = 2,
    power_of_two: bool = False,
    sort: str = "height",
) -> tuple[Image.Image, dict]:
    """Pack images with a shelf algorithm.

    items: [{"name": str, "image": PIL.Image, "pivot": {"x": int, "y": int}}]
    """

    if not items:
        raise ValueError("No images to pack")
    prepared = []
    for item in items:
        image = ensure_rgba(item["image"])
        prepared.append(
            {
                "name": item["name"],
                "image": image,
                "pivot": item.get("pivot"),
                "source": item.get("source"),
            }
        )
    if sort == "height":
        prepared.sort(key=lambda i: (-i["image"].height, -i["image"].width, i["name"]))
    elif sort == "area":
        prepared.sort(key=lambda i: -(i["image"].width * i["image"].height))
    elif sort == "name":
        prepared.sort(key=lambda i: i["name"])
    elif sort != "none":
        raise ValueError("sort must be height, area, name or none")

    max_item_w = max(i["image"].width for i in prepared)
    max_item_h = max(i["image"].height for i in prepared)
    if max_width < max_item_w + padding * 2:
        raise ValueError(
            f"max_width {max_width} cannot hold the widest item ({max_item_w}px) plus {padding * 2}px padding"
        )
    if max_height < max_item_h + padding * 2:
        raise ValueError(
            f"max_height {max_height} cannot hold the tallest item ({max_item_h}px) plus {padding * 2}px padding"
        )
    width = min(max_width, max(max_item_w + padding * 2, 64))
    if power_of_two:
        width = _next_power_of_two(width)
        if width > max_width:
            raise ValueError(f"power-of-two width {width} exceeds max_width {max_width}")
    placements = []
    x = padding
    y = padding
    shelf_h = 0
    for item in prepared:
        w, h = item["image"].size
        if x + w + padding > width:
            # Start a new shelf.
            y += shelf_h + padding
            x = padding
            shelf_h = 0
        if y + h + padding > max_height:
            raise ValueError("Atlas height exceeded; reduce image count or raise max-height")
        placements.append({"x": x, "y": y, "w": w, "h": h})
        x += w + padding
        shelf_h = max(shelf_h, h)
    height = y + shelf_h + padding
    if power_of_two:
        height = _next_power_of_two(height)
        if height > max_height:
            raise ValueError(f"power-of-two height {height} exceeds max_height {max_height}")
    sheet = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    frames = []
    for item, place in zip(prepared, placements):
        sheet.alpha_composite(item["image"], (place["x"], place["y"]))
        record = {
            "name": item["name"],
            "x": place["x"],
            "y": place["y"],
            "w": place["w"],
            "h": place["h"],
        }
        if item.get("source"):
            record["source"] = item["source"]
        if item.get("pivot"):
            record["pivot"] = item["pivot"]
        frames.append(record)
    meta = {
        "image": {"width": width, "height": height},
        "padding": padding,
        "power_of_two": power_of_two,
        "sort": sort,
        "frame_count": len(frames),
        "frames": frames,
    }
    return sheet, meta


def pack_files(
    paths: Sequence[str | Path],
    output_path: str | Path,
    metadata_path: str | Path | None = None,
    overwrite: bool = False,
    **kwargs,
) -> dict:
    items = []
    for path in paths:
        path = Path(path)
        items.append({"name": path.stem, "image": load_image(path), "source": str(path)})
    sheet, meta = pack_atlas(items, **kwargs)
    save_png(sheet, output_path, overwrite=overwrite)
    if metadata_path:
        write_json(metadata_path, meta)
    return meta
