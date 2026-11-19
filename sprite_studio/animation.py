"""Frame alignment, animation previews and animation validation."""

from __future__ import annotations

import hashlib
import math
import shutil
import tempfile
from pathlib import Path
from typing import Sequence

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageSequence

from .image_utils import (
    alpha_bbox,
    alpha_stats,
    checkerboard,
    default_font,
    ensure_rgba,
    flatten_on,
    load_image,
    natural_key,
    parse_color,
    resize_rgba,
    save_image,
    save_png,
    write_json,
)


def _bottom_center(bbox: tuple[int, int, int, int]) -> tuple[float, float]:
    x0, y0, x1, y1 = bbox
    return ((x0 + x1 + 1) / 2.0, float(y1 + 1))


def _center(bbox: tuple[int, int, int, int]) -> tuple[float, float]:
    x0, y0, x1, y1 = bbox
    return ((x0 + x1 + 1) / 2.0, (y0 + y1 + 1) / 2.0)


def align_frames(
    frames: Sequence[Image.Image],
    canvas_width: int | None = None,
    canvas_height: int | None = None,
    pivot_x: int | None = None,
    pivot_y: int | None = None,
    align: str = "bottom-center",
    align_y: bool = True,
    scale_mode: str = "none",
    target_height: int | None = None,
    resample: str = "nearest",
    allow_clip: bool = False,
) -> tuple[list[Image.Image], dict]:
    """Align frames to a shared canvas and pivot.

    align:
      bottom-center - put the lowest visible pixel at the pivot (walk/idle)
      center        - put the bounding-box centre at the pivot
      none          - only normalise the canvas; preserve authored offsets

    `align_y=False` aligns horizontally but keeps each frame's vertical position,
    which is useful for jump/fall frames whose height is intentional movement.
    """

    if not frames:
        raise ValueError("No frames to align")
    frames = [ensure_rgba(f) for f in frames]
    if canvas_width is None:
        canvas_width = max(f.width for f in frames)
    if canvas_height is None:
        canvas_height = max(f.height for f in frames)
    if canvas_width <= 0 or canvas_height <= 0:
        raise ValueError("Canvas dimensions must be positive")
    if pivot_x is None:
        pivot_x = canvas_width // 2
    if pivot_y is None:
        pivot_y = canvas_height
    if not (0 <= pivot_x <= canvas_width and 0 <= pivot_y <= canvas_height):
        raise ValueError(f"Pivot ({pivot_x}, {pivot_y}) is outside the canvas")

    # Optional scale normalisation.  This is deliberately opt-in: forcing every
    # frame to the same height destroys genuine squash/stretch and jump arcs.
    heights = []
    for frame in frames:
        bbox = alpha_bbox(frame)
        heights.append(bbox[3] - bbox[1] + 1 if bbox else 0)
    valid_heights = [h for h in heights if h > 0]
    if scale_mode not in {"none", "fit_height", "match_first"}:
        raise ValueError("scale_mode must be none, fit_height or match_first")
    if target_height is None and valid_heights:
        target_height = valid_heights[0]

    aligned: list[Image.Image] = []
    records = []
    for i, frame in enumerate(frames):
        original_bbox = alpha_bbox(frame)
        scale = 1.0
        working = frame
        if scale_mode != "none" and original_bbox and target_height:
            current_h = original_bbox[3] - original_bbox[1] + 1
            if current_h > 0:
                scale = target_height / current_h
                if abs(scale - 1.0) > 0.005:
                    new_w = max(1, round(frame.width * scale))
                    new_h = max(1, round(frame.height * scale))
                    working = resize_rgba(frame, new_w, new_h, resample)
        bbox = alpha_bbox(working)
        if bbox is None:
            x = 0
            y = 0
        else:
            if align == "bottom-center":
                ax, ay = _bottom_center(bbox)
            elif align == "center":
                ax, ay = _center(bbox)
            elif align == "none":
                ax, ay = float(pivot_x), float(pivot_y)
            else:
                raise ValueError("align must be bottom-center, center or none")
            x = round(pivot_x - ax)
            y = round(pivot_y - ay) if align_y else 0
        # If the source frame already has a larger canvas, keep authored
        # vertical offsets when align_y is false.
        if not align_y and working.size != (canvas_width, canvas_height) and bbox is not None:
            y = 0
        canvas = Image.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 0))
        # Compute clipping before compositing so we never silently cut art.
        left = max(0, -x)
        top = max(0, -y)
        right = min(working.width, canvas_width - x)
        bottom = min(working.height, canvas_height - y)
        clipped = left > 0 or top > 0 or right < working.width or bottom < working.height
        if clipped and not allow_clip:
            raise ValueError(
                f"Frame {i} would be clipped after alignment (offset {x},{y}, size {working.size}, "
                f"canvas {canvas_width}x{canvas_height}). Increase the canvas or pass --allow-clip."
            )
        paste_x = max(0, x)
        paste_y = max(0, y)
        if right > left and bottom > top:
            canvas.alpha_composite(working.crop((left, top, right, bottom)), (paste_x, paste_y))
        aligned.append(canvas)
        records.append(
            {
                "index": i,
                "original_bbox": list(original_bbox) if original_bbox else None,
                "scale": round(scale, 4),
                "offset_x": x,
                "offset_y": y,
                "aligned_bbox": list(alpha_bbox(canvas)) if alpha_bbox(canvas) else None,
                "clipped": clipped,
            }
        )
    report = {
        "canvas": {"width": canvas_width, "height": canvas_height},
        "pivot": {"x": pivot_x, "y": pivot_y},
        "align": align,
        "align_y": align_y,
        "scale_mode": scale_mode,
        "target_height": target_height,
        "frames": records,
        "clip_warnings": [r["index"] for r in records if r["clipped"]],
    }
    return aligned, report


def _duration_list(durations: Sequence[int] | None, count: int, fps: float = 10.0) -> list[int]:
    if durations is None:
        ms = max(10, round(1000 / fps))
        return [ms] * count
    if len(durations) != count:
        raise ValueError(f"Expected {count} durations, got {len(durations)}")
    out = [int(d) for d in durations]
    if any(d <= 0 for d in out):
        raise ValueError("Durations must be positive milliseconds")
    return out


def make_preview(
    frames: Sequence[Image.Image],
    output_path: str | Path,
    durations: Sequence[int] | None = None,
    fps: float = 10.0,
    loop: bool = True,
    background: str = "checker",
    size: tuple[int, int] | None = None,
    scale: int = 1,
    overwrite: bool = False,
    title: str | None = None,
) -> Path:
    """Write a GIF, APNG, WebP or MP4 preview.

    GIF is flattened onto a background because binary GIF transparency produces
    ugly fringes around anti-aliased art.  APNG and WebP preserve alpha.
    """

    if not frames:
        raise ValueError("No frames for preview")
    frames = [ensure_rgba(f) for f in frames]
    durations = _duration_list(durations, len(frames), fps=fps)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite {output_path}. Pass --overwrite.")
    suffix = output_path.suffix.lower()

    processed: list[Image.Image] = []
    for frame in frames:
        if size:
            frame = resize_rgba(frame, size[0], size[1], "nearest")
        elif scale != 1:
            frame = resize_rgba(frame, frame.width * scale, frame.height * scale, "nearest")
        processed.append(frame)

    if title:
        processed = [_with_title(f, title) for f in processed]

    if suffix == ".gif":
        flat = []
        for frame in processed:
            if background == "checker":
                bg = checkerboard(frame.width, frame.height, 8)
            elif background == "transparent":
                bg = Image.new("RGBA", frame.size, (0, 0, 0, 0))
            else:
                bg = Image.new("RGBA", frame.size, parse_color(background))
            if background == "transparent":
                # GIF supports one-bit transparency; use it only when requested.
                flat.append(frame.convert("P", palette=Image.Palette.ADAPTIVE, colors=255))
            else:
                bg.alpha_composite(frame)
                flat.append(bg.convert("RGB").convert("P", palette=Image.Palette.ADAPTIVE, colors=255))
        if background == "transparent":
            transparency = 0
            for im in flat:
                im.info["transparency"] = transparency
        flat[0].save(
            output_path,
            save_all=True,
            append_images=flat[1:],
            duration=durations,
            loop=0 if loop else 1,
            disposal=2,
            optimize=False,
        )
    elif suffix in {".png", ".apng"}:
        if background not in {"transparent", "checker"}:
            processed = [flatten_on(f, parse_color(background)) for f in processed]
        elif background == "checker":
            processed = [_flatten_checker(f) for f in processed]
        processed[0].save(
            output_path,
            save_all=True,
            append_images=processed[1:],
            duration=durations,
            loop=0 if loop else 1,
            disposal=2,
            blend=0,
        )
    elif suffix in {".webp"}:
        if background == "checker":
            processed = [_flatten_checker(f) for f in processed]
        elif background != "transparent":
            processed = [flatten_on(f, parse_color(background)) for f in processed]
        processed[0].save(
            output_path,
            save_all=True,
            append_images=processed[1:],
            duration=durations,
            loop=0 if loop else 1,
            lossless=True,
        )
    elif suffix in {".mp4", ".webm"}:
        _write_video(processed, durations, output_path, loop=loop, background=background)
    else:
        raise ValueError("Preview format must be .gif, .png/.apng, .webp, .mp4 or .webm")
    return output_path


def _flatten_checker(frame: Image.Image) -> Image.Image:
    bg = checkerboard(frame.width, frame.height, 8)
    bg.alpha_composite(frame)
    return bg


def _with_title(frame: Image.Image, title: str) -> Image.Image:
    canvas = Image.new("RGBA", (frame.width, frame.height + 24), (25, 25, 30, 255))
    canvas.alpha_composite(frame, (0, 24))
    draw = ImageDraw.Draw(canvas)
    draw.text((4, 4), title, fill=(240, 240, 245, 255), font=default_font(14))
    return canvas


def _write_video(frames: Sequence[Image.Image], durations: Sequence[int], path: Path, loop: bool, background: str):
    try:
        import imageio.v2 as imageio  # type: ignore
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("MP4/WebM preview requires imageio and imageio-ffmpeg") from exc
    fps = max(1.0, 1000.0 / float(np.median(durations)))
    if background == "checker":
        frames = [_flatten_checker(f) for f in frames]
    elif background != "transparent":
        frames = [flatten_on(f, parse_color(background)) for f in frames]
    # Video has no alpha in common players; flatten transparent output on a
    # neutral dark colour rather than emitting an invisible frame.
    if background == "transparent":
        frames = [flatten_on(f, (20, 20, 24, 255)) for f in frames]
    arrays = [np.asarray(f.convert("RGB")) for f in frames]
    writer = imageio.get_writer(str(path), fps=fps, codec="libx264", quality=8, macro_block_size=1)
    try:
        for _ in range(2 if loop else 1):
            for arr in arrays:
                writer.append_data(arr)
    finally:
        writer.close()


def _frame_signature(frame: Image.Image) -> str:
    return hashlib.sha256(frame.tobytes()).hexdigest()[:16]


def _difference_score(a: Image.Image, b: Image.Image) -> float:
    """Mean absolute RGBA difference on the union of visible areas."""

    if a.size != b.size:
        return 255.0
    aa = np.asarray(ensure_rgba(a), dtype=np.int16)
    bb = np.asarray(ensure_rgba(b), dtype=np.int16)
    mask = (aa[..., 3] > 0) | (bb[..., 3] > 0)
    if not mask.any():
        return 0.0
    diff = np.abs(aa - bb)
    # Weight RGB by alpha coverage so hidden RGB under alpha=0 is ignored.
    alpha_weight = np.maximum(aa[..., 3], bb[..., 3]).astype(np.float32) / 255.0
    rgb_diff = diff[..., :3].mean(axis=2) * alpha_weight
    alpha_diff = diff[..., 3].astype(np.float32)
    combined = (rgb_diff + alpha_diff) / 2.0
    return float(combined[mask].mean())


def validate_animation(
    frames: Sequence[Image.Image],
    expected_count: int | None = None,
    expected_size: tuple[int, int] | None = None,
    pivot: tuple[int, int] | None = None,
    loop: bool = True,
    durations: Sequence[int] | None = None,
    max_displacement: float = 12.0,
    max_scale_variation: float = 0.22,
    max_palette_drift: float = 28.0,
    max_loop_diff: float = 42.0,
    border_tolerance: float = 0.01,
    duplicate_tolerance: float = 0.0,
) -> dict:
    """Validate identity, scale, placement, loop and metadata consistency."""

    if not frames:
        raise ValueError("No frames to validate")
    frames = [ensure_rgba(f) for f in frames]
    checks = []

    def add(name: str, ok: bool, severity: str, detail: str, value=None):
        checks.append({"name": name, "ok": bool(ok), "severity": severity, "detail": detail, "value": value})

    if expected_count is not None:
        add("frame_count", len(frames) == expected_count, "critical", f"expected {expected_count}, got {len(frames)}", len(frames))
    else:
        add("frame_count", True, "critical", f"{len(frames)} frames", len(frames))

    sizes = {f.size for f in frames}
    size_ok = len(sizes) == 1 and (expected_size is None or next(iter(sizes)) == tuple(expected_size))
    add(
        "canvas_dimensions",
        size_ok,
        "critical",
        f"sizes={sorted(sizes)}" + (f", expected={expected_size}" if expected_size else ""),
        sorted([list(s) for s in sizes]),
    )

    empty = [i for i, f in enumerate(frames) if alpha_bbox(f) is None]
    add("empty_frames", len(empty) == 0, "critical", f"empty indices: {empty}" if empty else "no empty frames", empty)

    signatures = [_frame_signature(f) for f in frames]
    duplicates = []
    for i in range(1, len(signatures)):
        if signatures[i] == signatures[i - 1]:
            duplicates.append(i)
    # Near duplicates are useful diagnostics even when bytes differ.
    near_duplicates = []
    if duplicate_tolerance > 0:
        for i in range(1, len(frames)):
            if _difference_score(frames[i - 1], frames[i]) <= duplicate_tolerance:
                near_duplicates.append(i)
    add(
        "duplicate_frames",
        len(duplicates) == 0,
        "warning",
        f"identical adjacent indices: {duplicates}" if duplicates else "no identical adjacent frames",
        duplicates,
    )

    bboxes = [alpha_bbox(f) for f in frames]
    centers = [((b[0] + b[2] + 1) / 2, (b[1] + b[3] + 1) / 2) for b in bboxes if b]
    displacements = []
    for i in range(1, len(centers)):
        dx = centers[i][0] - centers[i - 1][0]
        dy = centers[i][1] - centers[i - 1][1]
        displacements.append(round(math.hypot(dx, dy), 2))
    max_disp = max(displacements) if displacements else 0.0
    add(
        "displacement",
        max_disp <= max_displacement,
        "warning",
        f"max centre displacement {max_disp}px (limit {max_displacement}px)",
        {"max": max_disp, "per_transition": displacements},
    )

    heights = [b[3] - b[1] + 1 for b in bboxes if b]
    if heights:
        median_h = float(np.median(heights))
        variation = (max(heights) - min(heights)) / median_h if median_h else 0.0
    else:
        variation = 0.0
        median_h = 0
    add(
        "scale_variation",
        variation <= max_scale_variation,
        "warning",
        f"height variation {variation:.3f} (limit {max_scale_variation:.3f})",
        {"variation": round(variation, 4), "heights": heights, "median": median_h},
    )

    drifts = []
    for i in range(1, len(frames)):
        a = np.asarray(frames[i - 1], dtype=np.float32)
        b = np.asarray(frames[i], dtype=np.float32)
        ma = a[..., 3] > 0
        mb = b[..., 3] > 0
        if ma.any() and mb.any():
            ca = a[..., :3][ma].mean(axis=0)
            cb = b[..., :3][mb].mean(axis=0)
            drifts.append(round(float(np.linalg.norm(ca - cb)), 2))
    max_drift = max(drifts) if drifts else 0.0
    add(
        "palette_drift",
        max_drift <= max_palette_drift,
        "warning",
        f"max mean-colour drift {max_drift} (limit {max_palette_drift})",
        {"max": max_drift, "per_transition": drifts},
    )

    if loop and len(frames) > 1:
        loop_diff = round(_difference_score(frames[-1], frames[0]), 2)
        add(
            "loop_transition",
            loop_diff <= max_loop_diff,
            "warning",
            f"last->first difference {loop_diff} (limit {max_loop_diff})",
            loop_diff,
        )
    else:
        add("loop_transition", True, "info", "not a looping animation", None)

    edge_artifacts = []
    for i, frame in enumerate(frames):
        arr = np.asarray(frame)
        edge_alpha = np.concatenate(
            [arr[0, :, 3], arr[-1, :, 3], arr[:, 0, 3], arr[:, -1, 3]]
        )
        ratio = float(np.count_nonzero(edge_alpha > 0) / max(1, len(edge_alpha)))
        if ratio > border_tolerance:
            edge_artifacts.append({"index": i, "edge_opaque_ratio": round(ratio, 4)})
    add(
        "canvas_edge_artifacts",
        len(edge_artifacts) == 0,
        "warning",
        "opaque pixels touch the canvas edge" if edge_artifacts else "clear edge padding",
        edge_artifacts,
    )

    if durations is not None:
        duration_ok = len(durations) == len(frames) and all(int(d) > 0 for d in durations)
        add("durations", duration_ok, "critical", f"{len(durations)} durations for {len(frames)} frames", list(durations))
    else:
        add("durations", True, "info", "uniform/fps-derived timing", None)

    if pivot is not None:
        add(
            "pivot",
            all(0 <= pivot[0] <= frames[0].width and 0 <= pivot[1] <= frames[0].height for _ in [0]),
            "critical",
            f"pivot {pivot} within {frames[0].size}",
            list(pivot),
        )

    critical_fail = [c for c in checks if not c["ok"] and c["severity"] == "critical"]
    warnings = [c for c in checks if not c["ok"] and c["severity"] == "warning"]
    status = "FAIL" if critical_fail else ("WARN" if warnings else "PASS")
    return {
        "status": status,
        "frames": len(frames),
        "checks": checks,
        "critical_failures": [c["name"] for c in critical_fail],
        "warnings": [c["name"] for c in warnings],
        "metrics": {
            "max_displacement": max_disp,
            "scale_variation": round(variation, 4),
            "max_palette_drift": max_drift,
            "duplicate_indices": duplicates,
            "near_duplicate_indices": near_duplicates,
            "edge_artifacts": edge_artifacts,
        },
    }


def preview_from_files(
    frame_paths: Sequence[str | Path],
    output_path: str | Path,
    durations: Sequence[int] | None = None,
    **kwargs,
) -> Path:
    frames = [load_image(p) for p in frame_paths]
    return make_preview(frames, output_path, durations=durations, **kwargs)
