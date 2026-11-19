"""Background removal and transparency cleanup.

The default removal strategy is *edge-connected*: it samples the border, then
removes only regions reachable from the border.  That protects an eye, gem or
highlight that happens to share a colour with the backdrop.  A global colour
key is available, but must be requested explicitly.
"""

from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import Sequence

import numpy as np
from PIL import Image, ImageFilter

from .image_utils import alpha_array, alpha_bbox, color_distance, color_hex, ensure_rgba, parse_color, save_png, write_json


def _border_pixels(rgba: np.ndarray, border: int = 2) -> np.ndarray:
    h, w = rgba.shape[:2]
    b = max(1, min(border, max(1, min(h, w) // 2)))
    parts = [
        rgba[:b, :, :3].reshape(-1, 3),
        rgba[-b:, :, :3].reshape(-1, 3),
        rgba[:, :b, :3].reshape(-1, 3),
        rgba[:, -b:, :3].reshape(-1, 3),
    ]
    return np.concatenate(parts, axis=0)


def suggest_background_colors(image: Image.Image, border: int = 2, tolerance: int = 26, max_colors: int = 6) -> list[dict]:
    """Cluster border colours and return likely backdrop colours."""

    rgba = np.asarray(ensure_rgba(image))
    pixels = _border_pixels(rgba, border)
    # Ignore already-transparent pixels.
    opaque = pixels[pixels[:, 3] > 0] if pixels.shape[1] == 4 else pixels
    if len(opaque) == 0:
        return []
    # Coarse buckets (16 levels/channel) make the sample robust to JPEG noise.
    buckets: dict[tuple[int, int, int], list[np.ndarray]] = {}
    for px in opaque[:, :3]:
        key = tuple(int(v) // 16 for v in px)
        buckets.setdefault(key, []).append(px)
    clusters = sorted(buckets.values(), key=len, reverse=True)[:max_colors]
    colors = []
    for cluster in clusters:
        if len(cluster) < max(4, len(opaque) * 0.005):
            continue
        arr = np.stack(cluster)
        median = tuple(int(v) for v in np.median(arr, axis=0))
        colors.append(
            {
                "rgb": list(median),
                "hex": color_hex(median),
                "border_pixels": len(cluster),
                "border_percent": round(len(cluster) / len(opaque) * 100, 2),
            }
        )
    # Merge colours that are perceptually very close.
    merged: list[dict] = []
    for item in colors:
        for existing in merged:
            if color_distance(item["rgb"], existing["rgb"]) <= tolerance / 3:
                existing["border_pixels"] += item["border_pixels"]
                existing["border_percent"] = round(existing["border_percent"] + item["border_percent"], 2)
                break
        else:
            merged.append(item)
    return merged


def _candidate_mask(rgba: np.ndarray, colors: Sequence[Sequence[int]], tolerance: int) -> np.ndarray:
    if not colors:
        return np.zeros(rgba.shape[:2], dtype=bool)
    rgb = rgba[..., :3].astype(np.int32)
    mask = np.zeros(rgba.shape[:2], dtype=bool)
    for color in colors:
        diff = rgb - np.array(color[:3], dtype=np.int32)
        dist = np.sqrt(np.sum(diff * diff, axis=2))
        mask |= dist <= tolerance
    return mask


def _border_connected(mask: np.ndarray) -> np.ndarray:
    """Return the subset of `mask` connected to an image border.

    scipy.ndimage.label is used when available.  The fallback is a breadth-first
    flood fill, which is slower but has no extra dependency.
    """

    try:
        from scipy import ndimage  # type: ignore

        labels, count = ndimage.label(mask, structure=np.ones((3, 3), dtype=int))
        if count == 0:
            return np.zeros_like(mask, dtype=bool)
        border_labels = set(np.unique(np.concatenate([labels[0, :], labels[-1, :], labels[:, 0], labels[:, -1]])))
        border_labels.discard(0)
        return np.isin(labels, list(border_labels))
    except Exception:
        pass

    h, w = mask.shape
    out = np.zeros_like(mask, dtype=bool)
    queue: deque[tuple[int, int]] = deque()
    for x in range(w):
        for y in (0, h - 1):
            if mask[y, x] and not out[y, x]:
                out[y, x] = True
                queue.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if mask[y, x] and not out[y, x]:
                out[y, x] = True
                queue.append((y, x))
    while queue:
        y, x = queue.popleft()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy == 0 and dx == 0:
                    continue
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not out[ny, nx]:
                    out[ny, nx] = True
                    queue.append((ny, nx))
    return out


def remove_background(
    image: Image.Image,
    tolerance: int = 28,
    border: int = 2,
    method: str = "edge",
    colors: Sequence[Sequence[int]] | None = None,
    feather: int = 0,
    alpha_floor: int = 0,
) -> tuple[Image.Image, dict]:
    """Remove a backdrop and return (RGBA image, report).

    method:
      edge   - only border-connected regions are removed (default, safest)
      global - every pixel within tolerance of the sampled colours is removed
      none   - no removal; useful for inspecting the report
    """

    method = method.lower()
    if method not in {"edge", "global", "none"}:
        raise ValueError("method must be edge, global or none")
    rgba_image = ensure_rgba(image)
    rgba = np.asarray(rgba_image).copy()
    suggested = suggest_background_colors(rgba_image, border=border, tolerance=tolerance)
    chosen = [list(c) for c in colors] if colors else [c["rgb"] for c in suggested]
    mask = _candidate_mask(rgba, chosen, tolerance)
    if method == "edge":
        removal = _border_connected(mask)
    elif method == "global":
        removal = mask
    else:
        removal = np.zeros_like(mask, dtype=bool)
    # Never remove pixels that are already transparent; they have no colour to
    # contribute and counting them would inflate the report.
    removal &= rgba[..., 3] > 0
    removed_pixels = int(np.count_nonzero(removal))
    rgba[..., 3] = np.where(removal, 0, rgba[..., 3])

    if feather > 0 and removal.any():
        # Soften the cut only near the boundary.  Blurring the *removal* mask
        # and multiplying alpha preserves interior opacity.
        m = Image.fromarray((removal * 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(feather))
        soft = 1.0 - np.asarray(m, dtype=np.float32) / 255.0
        rgba[..., 3] = np.clip(rgba[..., 3].astype(np.float32) * soft, 0, 255).astype(np.uint8)

    if alpha_floor > 0:
        a = rgba[..., 3]
        rgba[..., 3] = np.where(a <= alpha_floor, 0, a)

    result = Image.fromarray(rgba, "RGBA")
    # Residual backdrop estimate: opaque pixels remaining on the outer border.
    b = max(1, border)
    border_alpha = np.concatenate(
        [
            rgba[:b, :, 3].ravel(),
            rgba[-b:, :, 3].ravel(),
            rgba[:, :b, 3].ravel(),
            rgba[:, -b:, 3].ravel(),
        ]
    )
    border_opaque = int(np.count_nonzero(border_alpha > 0))
    border_total = int(border_alpha.size)
    report = {
        "method": method,
        "tolerance": tolerance,
        "border_sample": border,
        "suggested_background_colours": suggested,
        "colours_used": [{"rgb": [int(v) for v in c[:3]], "hex": color_hex(c)} for c in chosen],
        "removed_pixels": removed_pixels,
        "remaining_visible_pixels": int(np.count_nonzero(rgba[..., 3] > 0)),
        "border_opaque_pixels": border_opaque,
        "border_residual_percent": round(border_opaque / border_total * 100, 2) if border_total else 0.0,
        "alpha_bbox": list(alpha_bbox(result)) if alpha_bbox(result) else None,
        "warning": None,
    }
    if border_opaque > border_total * 0.02:
        report["warning"] = (
            "The outer border still contains opaque pixels. Inspect the mask; the background may "
            "be textured, or the subject may extend to the canvas edge."
        )
    return result, report


def _label_components(mask: np.ndarray) -> tuple[np.ndarray, int]:
    try:
        from scipy import ndimage  # type: ignore

        labels, count = ndimage.label(mask, structure=np.ones((3, 3), dtype=int))
        return labels, int(count)
    except Exception:
        pass
    h, w = mask.shape
    labels = np.zeros((h, w), dtype=np.int32)
    queue: deque[tuple[int, int]] = deque()
    count = 0
    for y in range(h):
        for x in range(w):
            if mask[y, x] and labels[y, x] == 0:
                count += 1
                labels[y, x] = count
                queue.append((y, x))
                while queue:
                    cy, cx = queue.popleft()
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            ny, nx = cy + dy, cx + dx
                            if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and labels[ny, nx] == 0:
                                labels[ny, nx] = count
                                queue.append((ny, nx))
    return labels, count


def clean_transparency(
    image: Image.Image,
    min_island: int = 4,
    alpha_floor: int = 0,
    fill_holes: bool = False,
    preserve_largest: bool = True,
    smooth: int = 0,
) -> tuple[Image.Image, dict]:
    """Remove tiny alpha islands and optionally fill enclosed holes.

    `min_island` is intentionally small by default.  A 2-pixel sparkle can be a
    deliberate detail; the report lists every removed component so the decision
    remains auditable.
    """

    rgba = np.asarray(ensure_rgba(image)).copy()
    alpha = rgba[..., 3]
    visible = alpha > alpha_floor if alpha_floor else alpha > 0
    removed_components = []
    before_visible = int(np.count_nonzero(visible))

    if min_island > 0 and visible.any():
        labels, count = _label_components(visible)
        if count:
            sizes = np.bincount(labels.ravel())
            # label 0 is background; find largest foreground component
            foreground = sizes.copy()
            foreground[0] = 0
            largest_label = int(np.argmax(foreground))
            keep = np.zeros(count + 1, dtype=bool)
            for label in range(1, count + 1):
                size = int(sizes[label])
                if size >= min_island or (preserve_largest and label == largest_label):
                    keep[label] = True
                else:
                    removed_components.append(
                        {
                            "label": label,
                            "pixels": size,
                            "centroid_xy": _centroid(labels == label),
                        }
                    )
            keep_mask = keep[labels]
            alpha = np.where(visible & keep_mask, alpha, 0)
            rgba[..., 3] = alpha
            visible = alpha > 0

    if alpha_floor > 0:
        rgba[..., 3] = np.where(rgba[..., 3] <= alpha_floor, 0, rgba[..., 3])
        visible = rgba[..., 3] > 0

    filled_pixels = 0
    if fill_holes and visible.any():
        transparent = ~visible
        labels, count = _label_components(transparent)
        if count:
            border_labels = set(np.unique(np.concatenate([labels[0, :], labels[-1, :], labels[:, 0], labels[:, -1]])))
            border_labels.discard(0)
            hole_mask = transparent & ~np.isin(labels, list(border_labels))
            filled_pixels = int(np.count_nonzero(hole_mask))
            if filled_pixels:
                # Copy the median visible colour into enclosed holes; alpha 255.
                colour = np.median(rgba[..., :3][visible], axis=0)
                rgba[..., :3][hole_mask] = colour.astype(np.uint8)
                rgba[..., 3][hole_mask] = 255
                visible = rgba[..., 3] > 0

    if smooth > 0 and visible.any():
        a = Image.fromarray(rgba[..., 3], "L").filter(ImageFilter.GaussianBlur(smooth))
        rgba[..., 3] = np.asarray(a, dtype=np.uint8)

    result = Image.fromarray(rgba, "RGBA")
    report = {
        "min_island": min_island,
        "alpha_floor": alpha_floor,
        "fill_holes": fill_holes,
        "removed_components": removed_components,
        "removed_component_count": len(removed_components),
        "removed_pixels": before_visible - int(np.count_nonzero(rgba[..., 3] > 0)),
        "filled_hole_pixels": filled_pixels,
        "remaining_visible_pixels": int(np.count_nonzero(rgba[..., 3] > 0)),
        "alpha_bbox": list(alpha_bbox(result)) if alpha_bbox(result) else None,
    }
    return result, report


def _centroid(mask: np.ndarray) -> list[float] | None:
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return None
    return [round(float(xs.mean()), 2), round(float(ys.mean()), 2)]


def remove_background_cli(
    input_path: str | Path,
    output_path: str | Path,
    report_path: str | Path | None = None,
    overwrite: bool = False,
    **kwargs,
) -> dict:
    image = ensure_rgba(Image.open(input_path))
    result, report = remove_background(image, **kwargs)
    save_png(result, output_path, overwrite=overwrite)
    if report_path:
        write_json(report_path, report)
    return report
