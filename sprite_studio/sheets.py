"""Sprite-sheet slicing, assembly and contact sheets."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Sequence

from PIL import Image, ImageDraw

from .image_utils import (
    alpha_bbox,
    default_font,
    ensure_rgba,
    fit_preview,
    load_image,
    natural_key,
    save_png,
    write_json,
)


def slice_sheet(
    image: Image.Image,
    columns: int | None = None,
    rows: int | None = None,
    cell_width: int | None = None,
    cell_height: int | None = None,
    margin: int = 0,
    spacing: int = 0,
    skip_empty: bool = True,
    prefix: str = "frame",
    out_dir: str | Path = ".",
    overwrite: bool = False,
) -> dict:
    """Slice a grid sheet and write individual PNG frames.

    The layout is never guessed from the image content.  Supply columns/rows or
    cell dimensions (or both) so the result is deterministic and auditable.
    """

    image = ensure_rgba(image)
    if columns is None and cell_width is None:
        raise ValueError("Provide --columns or --cell-width")
    if rows is None and cell_height is None:
        raise ValueError("Provide --rows or --cell-height")
    if columns is not None and columns <= 0:
        raise ValueError("columns must be positive")
    if rows is not None and rows <= 0:
        raise ValueError("rows must be positive")
    if margin < 0 or spacing < 0:
        raise ValueError("margin and spacing cannot be negative")

    usable_w = image.width - 2 * margin
    usable_h = image.height - 2 * margin
    if columns is None:
        assert cell_width is not None
        columns = (usable_w + spacing) // (cell_width + spacing)
    if rows is None:
        assert cell_height is not None
        rows = (usable_h + spacing) // (cell_height + spacing)
    if cell_width is None:
        cell_width = (usable_w - spacing * (columns - 1)) // columns
    if cell_height is None:
        cell_height = (usable_h - spacing * (rows - 1)) // rows
    if cell_width <= 0 or cell_height <= 0:
        raise ValueError("Computed cell size is not positive; check margin/spacing/columns/rows")

    expected_w = margin * 2 + columns * cell_width + (columns - 1) * spacing
    expected_h = margin * 2 + rows * cell_height + (rows - 1) * spacing
    if expected_w > image.width or expected_h > image.height:
        raise ValueError(
            f"Grid ({columns}x{rows} cells at {cell_width}x{cell_height}) does not fit "
            f"inside the {image.width}x{image.height} sheet"
        )

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    frames = []
    empty_cells = []
    index = 0
    for row in range(rows):
        for col in range(columns):
            x = margin + col * (cell_width + spacing)
            y = margin + row * (cell_height + spacing)
            cell = image.crop((x, y, x + cell_width, y + cell_height))
            bbox = alpha_bbox(cell)
            if bbox is None:
                empty_cells.append({"row": row, "column": col, "index": index})
                if skip_empty:
                    index += 1
                    continue
            filename = f"{prefix}__frame_{index:03d}.png"
            path = out_dir / filename
            save_png(cell, path, overwrite=overwrite)
            frames.append(
                {
                    "index": index,
                    "row": row,
                    "column": col,
                    "x": x,
                    "y": y,
                    "width": cell_width,
                    "height": cell_height,
                    "file": filename,
                    "content_bbox": list(bbox) if bbox else None,
                }
            )
            index += 1

    metadata = {
        "source": {
            "width": image.width,
            "height": image.height,
        },
        "layout": {
            "columns": columns,
            "rows": rows,
            "cell_width": cell_width,
            "cell_height": cell_height,
            "margin": margin,
            "spacing": spacing,
            "skip_empty": skip_empty,
        },
        "frame_count": len(frames),
        "empty_cells": empty_cells,
        "empty_cell_count": len(empty_cells),
        "empty_cells_written": not skip_empty,
        "frames": frames,
    }
    return metadata


def _layout_geometry(
    count: int,
    columns: int | None,
    rows: int | None,
    layout: str,
) -> tuple[int, int]:
    layout = layout.lower()
    if layout == "horizontal":
        return count, 1
    if layout == "vertical":
        return 1, count
    if layout != "grid":
        raise ValueError("layout must be grid, horizontal or vertical")
    if columns is None and rows is None:
        columns = max(1, math.ceil(math.sqrt(count)))
    elif columns is None:
        assert rows is not None
        columns = max(1, math.ceil(count / rows))
    elif rows is None:
        rows = max(1, math.ceil(count / columns))
    assert columns is not None and rows is not None
    if columns * rows < count:
        raise ValueError(f"{columns}x{rows} grid cannot hold {count} frames")
    return columns, rows


def build_sheet(
    frames: Sequence[Image.Image],
    layout: str = "horizontal",
    columns: int | None = None,
    rows: int | None = None,
    cell_width: int | None = None,
    cell_height: int | None = None,
    spacing: int = 0,
    margin: int = 0,
    background: tuple[int, int, int, int] = (0, 0, 0, 0),
    durations: Sequence[int] | None = None,
    metadata: dict | None = None,
) -> tuple[Image.Image, dict]:
    if not frames:
        raise ValueError("No frames to assemble")
    frames = [ensure_rgba(f) for f in frames]
    if cell_width is None:
        cell_width = max(f.width for f in frames)
    if cell_height is None:
        cell_height = max(f.height for f in frames)
    if cell_width <= 0 or cell_height <= 0:
        raise ValueError("Cell dimensions must be positive")
    too_large = [(i, f.size) for i, f in enumerate(frames) if f.width > cell_width or f.height > cell_height]
    if too_large:
        raise ValueError(f"Frames larger than the requested cell size: {too_large}")

    columns, rows = _layout_geometry(len(frames), columns, rows, layout)
    width = margin * 2 + columns * cell_width + (columns - 1) * spacing
    height = margin * 2 + rows * cell_height + (rows - 1) * spacing
    sheet = Image.new("RGBA", (width, height), background)
    frame_records = []
    for i, frame in enumerate(frames):
        col = i % columns
        row = i // columns
        x = margin + col * (cell_width + spacing)
        y = margin + row * (cell_height + spacing)
        # Preserve the frame's own pixels; pad transparently in the cell.
        px = x + (cell_width - frame.width) // 2
        py = y + (cell_height - frame.height) // 2
        sheet.alpha_composite(frame, (px, py))
        record = {
            "index": i,
            "x": px,
            "y": py,
            "width": frame.width,
            "height": frame.height,
            "cell_x": x,
            "cell_y": y,
            "cell_width": cell_width,
            "cell_height": cell_height,
        }
        if durations:
            record["duration_ms"] = int(durations[i])
        frame_records.append(record)

    meta = {
        "sheet": {
            "width": width,
            "height": height,
            "layout": layout,
            "columns": columns,
            "rows": rows,
            "cell_width": cell_width,
            "cell_height": cell_height,
            "spacing": spacing,
            "margin": margin,
        },
        "frame_count": len(frames),
        "frames": frame_records,
    }
    if metadata:
        meta.update(metadata)
    return sheet, meta


def contact_sheet(
    frames: Sequence[Image.Image | str | Path],
    labels: Sequence[str] | None = None,
    columns: int = 4,
    thumb_width: int = 128,
    thumb_height: int = 128,
    background: str = "checker",
    title: str | None = None,
    font_size: int = 12,
) -> Image.Image:
    if not frames:
        raise ValueError("No frames for contact sheet")
    images = [load_image(f) if isinstance(f, (str, Path)) else ensure_rgba(f) for f in frames]
    if labels is None:
        labels = [
            Path(f).name if isinstance(f, (str, Path)) else f"frame {i + 1:03d}"
            for i, f in enumerate(frames)
        ]
    if len(labels) != len(images):
        raise ValueError("labels must have the same length as frames")
    columns = max(1, columns)
    rows = math.ceil(len(images) / columns)
    cell_w = thumb_width
    cell_h = thumb_height + font_size + 12
    pad = 8
    title_h = 30 if title else 0
    width = pad + columns * (cell_w + pad)
    height = title_h + pad + rows * (cell_h + pad)
    canvas = Image.new("RGBA", (width, height), (32, 32, 38, 255))
    draw = ImageDraw.Draw(canvas)
    font = default_font(font_size)
    title_font = default_font(18)
    if title:
        draw.text((pad, 7), title, fill=(245, 245, 245, 255), font=title_font)
    for i, (image, label) in enumerate(zip(images, labels)):
        col = i % columns
        row = i // columns
        x = pad + col * (cell_w + pad)
        y = title_h + pad + row * (cell_h + pad)
        preview = fit_preview(image, (cell_w, thumb_height), "checker" if background == "checker" else background)
        canvas.alpha_composite(preview, (x, y))
        draw.rectangle([x, y, x + cell_w - 1, y + thumb_height - 1], outline=(90, 90, 100, 255))
        draw.text((x + 2, y + thumb_height + 2), label[:48], fill=(230, 230, 235, 255), font=font)
    return canvas


def assemble_from_files(
    frame_paths: Sequence[str | Path],
    output_path: str | Path,
    metadata_path: str | Path | None = None,
    overwrite: bool = False,
    **kwargs,
) -> dict:
    frames = [load_image(p) for p in frame_paths]
    sheet, meta = build_sheet(frames, **kwargs)
    save_png(sheet, output_path, overwrite=overwrite)
    if metadata_path:
        write_json(metadata_path, meta)
    return meta


def find_frames(folder: str | Path) -> list[Path]:
    folder = Path(folder)
    if not folder.is_dir():
        raise NotADirectoryError(f"Not a directory: {folder}")
    paths = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in {".png", ".webp"}]
    return sorted(paths, key=lambda p: natural_key(p.name))
