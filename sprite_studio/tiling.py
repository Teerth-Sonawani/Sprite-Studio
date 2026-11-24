"""Seamless-tile diagnostics and assembled previews."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from .image_utils import ensure_rgba, save_png


def _edge_pairs(rgba: np.ndarray, axis: str):
    if axis == "x":
        left = rgba[:, 0, :].astype(np.float32)
        right = rgba[:, -1, :].astype(np.float32)
        interior = np.abs(rgba[:, 1:, :].astype(np.float32) - rgba[:, :-1, :].astype(np.float32))
        return left, right, interior
    top = rgba[0, :, :].astype(np.float32)
    bottom = rgba[-1, :, :].astype(np.float32)
    interior = np.abs(rgba[1:, :, :].astype(np.float32) - rgba[:-1, :, :].astype(np.float32))
    return top, bottom, interior


def seam_report(image: Image.Image, threshold: float = 2.0, max_edge_diff: float = 48.0) -> dict:
    """Compare wrapping edges against the image's own interior gradient.

    A seamless tile does not require the two opposite edge columns to be
    identical; it requires the transition across the wrap to look like an
    ordinary interior transition.  The ratio `seam / interior` captures that.
    """

    rgba = np.asarray(ensure_rgba(image), dtype=np.uint8)
    if rgba.shape[0] < 3 or rgba.shape[1] < 3:
        raise ValueError("Tile must be at least 3x3 pixels")
    results = {}
    for axis in ("x", "y"):
        first, second, interior = _edge_pairs(rgba, axis)
        edge_diff = float(np.abs(first - second).mean())
        interior_mean = float(interior.mean()) if interior.size else 0.0
        ratio = edge_diff / max(interior_mean, 0.5)
        results[axis] = {
            "edge_mean_abs_diff": round(edge_diff, 3),
            "interior_mean_abs_diff": round(interior_mean, 3),
            "seam_ratio": round(ratio, 3),
            "passes_ratio": ratio <= threshold,
            "passes_absolute": edge_diff <= max_edge_diff,
        }
    overall = all(v["passes_ratio"] or v["passes_absolute"] for v in results.values())
    return {
        "status": "PASS" if overall else "WARN",
        "threshold_ratio": threshold,
        "max_edge_diff": max_edge_diff,
        "axes": results,
        "note": (
            "A warning means the wrap transition is measurably harsher than the tile's interior. "
            "Inspect the 2x2 wrap preview before rejecting: stylised tiles can legitimately have "
            "a strong boundary."
        ),
    }


def wrap_preview(image: Image.Image, tiles: int = 2) -> Image.Image:
    image = ensure_rgba(image)
    tiles = max(2, int(tiles))
    canvas = Image.new("RGBA", (image.width * tiles, image.height * tiles), (0, 0, 0, 0))
    for y in range(tiles):
        for x in range(tiles):
            canvas.alpha_composite(image, (x * image.width, y * image.height))
    return canvas


def assembled_preview(image: Image.Image, grid: int = 3, background: str = "checker") -> Image.Image:
    image = ensure_rgba(image)
    grid = max(1, int(grid))
    canvas = wrap_preview(image, grid)
    if background == "checker":
        from .image_utils import checkerboard

        base = checkerboard(canvas.width, canvas.height, 16)
        base.alpha_composite(canvas)
        canvas = base
    elif background != "transparent":
        from .image_utils import parse_color

        base = Image.new("RGBA", canvas.size, parse_color(background))
        base.alpha_composite(canvas)
        canvas = base
    draw = ImageDraw.Draw(canvas)
    # Show tile boundaries faintly so the reviewer can see the repeat.
    for i in range(1, grid):
        draw.line([(i * image.width, 0), (i * image.width, canvas.height)], fill=(255, 90, 90, 70), width=1)
        draw.line([(0, i * image.height), (canvas.width, i * image.height)], fill=(255, 90, 90, 70), width=1)
    return canvas


def tile_contact_sheet(image: Image.Image, output_path: str | Path, grid: int = 3, overwrite: bool = False) -> Path:
    preview = assembled_preview(image, grid=grid)
    return save_png(preview, output_path, overwrite=overwrite)
