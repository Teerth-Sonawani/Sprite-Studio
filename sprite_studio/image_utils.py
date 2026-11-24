"""Image loading, geometry, colour and preview helpers.

Only Pillow and NumPy are required.  Optional features (for example MP4 export)
fail with a clear message when their dependency is unavailable.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Pillow 10+ moved the resampling enum.  Support both old and new names.
NEAREST = getattr(Image, "Resampling", Image).NEAREST
BOX = getattr(Image, "Resampling", Image).BOX
BILINEAR = getattr(Image, "Resampling", Image).BILINEAR
BICUBIC = getattr(Image, "Resampling", Image).BICUBIC
LANCZOS = getattr(Image, "Resampling", Image).LANCZOS

RESAMPLE_METHODS = {
    "nearest": NEAREST,
    "box": BOX,
    "bilinear": BILINEAR,
    "bicubic": BICUBIC,
    "lanczos": LANCZOS,
}


def load_image(path: str | Path, mode: str | None = "RGBA") -> Image.Image:
    """Open an image and optionally convert it.

    `Image.open` is lazy; `.load()` forces a complete decode so corrupt files
    fail here rather than halfway through a batch.
    """

    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Image not found: {path}")
    try:
        opened = Image.open(path)
        opened.load()
        image: Image.Image = opened.convert(mode) if mode else opened
        return image
    except Exception as exc:  # Pillow raises several different exception types
        raise ValueError(f"Cannot read image {path}: {exc}") from exc


def ensure_rgba(image: Image.Image) -> Image.Image:
    return image if image.mode == "RGBA" else image.convert("RGBA")


def save_image(image: Image.Image, path: str | Path, overwrite: bool = False, **save_kwargs) -> Path:
    """Save an image, refusing to replace an existing file by default."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite {path}. Pass --overwrite to replace it.")
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"} and image.mode == "RGBA":
        # JPEG has no alpha.  Flatten explicitly rather than letting Pillow
        # silently produce a black background.
        image = flatten_on(image, (255, 255, 255, 255))
    image.save(path, **save_kwargs)
    return path


def save_png(image: Image.Image, path: str | Path, overwrite: bool = False, optimize: bool = True) -> Path:
    return save_image(image, path, overwrite=overwrite, format="PNG", optimize=optimize)


def alpha_array(image: Image.Image) -> np.ndarray:
    return np.asarray(ensure_rgba(image).getchannel("A"), dtype=np.uint8)


def alpha_bbox(image: Image.Image, threshold: int = 0) -> tuple[int, int, int, int] | None:
    """Return the inclusive pixel bounding box of visible content."""

    if threshold <= 0:
        mask = alpha_array(image) > 0
    else:
        mask = alpha_array(image) >= threshold
    if not mask.any():
        return None
    ys, xs = np.where(mask)
    return int(np.min(xs)), int(np.min(ys)), int(np.max(xs)), int(np.max(ys))


def alpha_stats(image: Image.Image) -> dict:
    a = alpha_array(image)
    total = int(a.size)
    opaque = int(np.count_nonzero(a == 255))
    transparent = int(np.count_nonzero(a == 0))
    partial = total - opaque - transparent
    bbox = alpha_bbox(image)
    return {
        "width": image.width,
        "height": image.height,
        "total_pixels": total,
        "opaque_pixels": opaque,
        "transparent_pixels": transparent,
        "partial_pixels": partial,
        "coverage": round((opaque + partial) / total, 6) if total else 0.0,
        "bbox": list(bbox) if bbox else None,
    }


def trim(image: Image.Image, padding: int = 0, threshold: int = 0) -> tuple[Image.Image, tuple[int, int, int, int] | None]:
    """Crop to the visible subject, adding optional transparent padding."""

    bbox = alpha_bbox(image, threshold)
    if bbox is None:
        return ensure_rgba(image), None
    x0, y0, x1, y1 = bbox
    x0 = max(0, x0 - padding)
    y0 = max(0, y0 - padding)
    x1 = min(image.width - 1, x1 + padding)
    y1 = min(image.height - 1, y1 + padding)
    return ensure_rgba(image).crop((x0, y0, x1 + 1, y1 + 1)), bbox


def pad_to_canvas(
    image: Image.Image,
    width: int,
    height: int,
    anchor: str = "center",
    background: tuple[int, int, int, int] = (0, 0, 0, 0),
) -> Image.Image:
    """Place an image on a larger canvas using a named anchor.

    The image is never scaled.  If it does not fit, a ValueError is raised so
    callers cannot accidentally clip artwork while "padding" it.
    """

    if image.width > width or image.height > height:
        raise ValueError(f"Image {image.size} does not fit in canvas {(width, height)}")
    canvas = Image.new("RGBA", (width, height), background)
    x, y = anchor_offset(image.size, (width, height), anchor)
    canvas.alpha_composite(image, (x, y))
    return canvas


def anchor_offset(
    content_size: tuple[int, int],
    canvas_size: tuple[int, int],
    anchor: str = "center",
) -> tuple[int, int]:
    cw, ch = content_size
    W, H = canvas_size
    horizontal = {
        "left": 0,
        "center": (W - cw) // 2,
        "right": W - cw,
    }
    vertical = {
        "top": 0,
        "center": (H - ch) // 2,
        "bottom": H - ch,
    }
    mapping = {
        "center": ("center", "center"),
        "top-left": ("left", "top"),
        "top": ("center", "top"),
        "top-center": ("center", "top"),
        "top-right": ("right", "top"),
        "left": ("left", "center"),
        "center-left": ("left", "center"),
        "center-right": ("right", "center"),
        "right": ("right", "center"),
        "bottom-left": ("left", "bottom"),
        "bottom": ("center", "bottom"),
        "bottom-center": ("center", "bottom"),
        "bottom-right": ("right", "bottom"),
    }
    if anchor not in mapping:
        raise ValueError(f"Unknown anchor {anchor!r}; choose from {', '.join(mapping)}")
    h, v = mapping[anchor]
    return horizontal[h], vertical[v]


def fit_canvas(
    image: Image.Image,
    width: int,
    height: int,
    anchor: str = "center",
    allow_crop: bool = False,
) -> Image.Image:
    x, y = anchor_offset(image.size, (width, height), anchor)
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    if allow_crop:
        # Crop only when explicitly requested; otherwise fail rather than
        # silently cut off a horn, sword or drop shadow.
        source = image.crop((-x, -y, -x + width, -y + height))
        canvas.alpha_composite(source, (0, 0))
        return canvas
    canvas.alpha_composite(image, (x, y))
    return canvas


def resize_rgba(image: Image.Image, width: int, height: int, method: str = "lanczos") -> Image.Image:
    """Resize RGBA without dark fringes.

    Pillow resizes straight (non-premultiplied) alpha, which lets hidden RGB
    bleed into transparent pixels.  Premultiplying first gives clean edges for
    painted art; nearest-neighbour is used untouched for pixel art.
    """

    if width <= 0 or height <= 0:
        raise ValueError("Resize dimensions must be positive")
    method = method.lower()
    if method not in RESAMPLE_METHODS:
        raise ValueError(f"Unknown resample method {method!r}; choose from {sorted(RESAMPLE_METHODS)}")
    image = ensure_rgba(image)
    if image.size == (width, height):
        return image.copy()
    resample = RESAMPLE_METHODS[method]
    if resample == NEAREST:
        return image.resize((width, height), NEAREST)
    arr = np.asarray(image, dtype=np.float32)
    alpha = arr[..., 3:4] / 255.0
    premultiplied = np.concatenate([arr[..., :3] * alpha, arr[..., 3:4]], axis=2)
    # Resize colour and alpha in one pass, then undo premultiplication.
    pm_image = Image.fromarray(np.clip(premultiplied + 0.5, 0, 255).astype(np.uint8), "RGBA")
    pm_image = pm_image.resize((width, height), resample)
    out = np.asarray(pm_image, dtype=np.float32)
    a = out[..., 3:4]
    rgb = np.divide(out[..., :3], a / 255.0, out=np.zeros_like(out[..., :3]), where=a > 0)
    out[..., :3] = np.clip(rgb, 0, 255)
    return Image.fromarray(out.astype(np.uint8), "RGBA")


def resize_to_fit(
    image: Image.Image,
    max_width: int,
    max_height: int,
    method: str = "lanczos",
    allow_upscale: bool = False,
) -> Image.Image:
    """Aspect-preserving resize inside a box; never upscales by default."""

    ratio = min(max_width / image.width, max_height / image.height)
    if not allow_upscale:
        ratio = min(ratio, 1.0)
    return resize_rgba(image, max(1, round(image.width * ratio)), max(1, round(image.height * ratio)), method)


def integer_scale(image: Image.Image, factor: int) -> Image.Image:
    if factor < 1:
        raise ValueError("Integer scale factor must be >= 1")
    return image.resize((image.width * factor, image.height * factor), NEAREST)


def color_hex(color: Sequence[int]) -> str:
    if len(color) == 4 and color[3] < 255:
        return "#%02x%02x%02x%02x" % tuple(int(c) for c in color)
    return "#%02x%02x%02x" % tuple(int(c) for c in color[:3])


def palette(image: Image.Image, max_colors: int = 32, alpha_threshold: int = 8) -> list[dict]:
    """Extract the dominant colours from visible pixels.

    Colours are sorted by pixel count.  Fully transparent pixels are ignored,
    which matters because generators often put arbitrary RGB beneath alpha=0.
    """

    rgba = np.asarray(ensure_rgba(image))
    visible = rgba[..., 3] >= alpha_threshold
    pixels = rgba[visible][:, :3]
    if len(pixels) == 0:
        return []
    # Quantize to RGB tuples, then merge near-identical values with a coarse
    # bucket only when the image has more unique colours than requested.
    unique, counts = np.unique(pixels.reshape(-1, 3), axis=0, return_counts=True)
    if len(unique) > max_colors:
        # Quantize only visible pixels.  Quantizing the full image would let the
        # arbitrary RGB values hidden beneath alpha=0 consume palette entries.
        pixels = rgba[visible][:, :3]
        strip = Image.fromarray(pixels.reshape(1, -1, 3), "RGB")
        q = strip.quantize(colors=max_colors, method=Image.Quantize.MEDIANCUT)
        pal = q.getpalette() or []
        q_counts = np.bincount(np.asarray(q).ravel(), minlength=max_colors)
        out: list[dict[str, Any]] = []
        for i, bin_count in enumerate(q_counts):
            if bin_count == 0 or i * 3 + 2 >= len(pal):
                continue
            rgb = tuple(pal[i * 3 : i * 3 + 3])
            out.append({"hex": color_hex(rgb), "rgb": list(rgb), "pixels": int(bin_count)})
        out.sort(key=lambda item: item["pixels"], reverse=True)
        total = sum(item["pixels"] for item in out) or 1
        for item in out:
            item["percent"] = round(item["pixels"] / total * 100, 2)
        return out
    order = np.argsort(-counts)
    total = int(counts.sum())
    out = []
    for idx in order[:max_colors]:
        rgb = tuple(int(v) for v in unique[idx])
        count = int(counts[idx])
        out.append(
            {
                "hex": color_hex(rgb),
                "rgb": list(rgb),
                "pixels": count,
                "percent": round(count / total * 100, 2),
            }
        )
    return out


def mean_color(image: Image.Image, alpha_threshold: int = 8) -> tuple[float, float, float] | None:
    arr = np.asarray(ensure_rgba(image), dtype=np.float32)
    mask = arr[..., 3] >= alpha_threshold
    if not mask.any():
        return None
    rgb = arr[..., :3][mask]
    means = rgb.mean(axis=0)
    return (float(means[0]), float(means[1]), float(means[2]))


def color_distance(a: Sequence[int], b: Sequence[int]) -> float:
    return math.sqrt(sum((float(x) - float(y)) ** 2 for x, y in zip(a[:3], b[:3])))


def flatten_on(image: Image.Image, background: tuple[int, int, int, int]) -> Image.Image:
    bg = Image.new("RGBA", image.size, background)
    bg.alpha_composite(ensure_rgba(image))
    return bg


def checkerboard(
    width: int,
    height: int,
    size: int = 8,
    colors: tuple[tuple[int, int, int, int], tuple[int, int, int, int]] = (
        (238, 238, 238, 255),
        (202, 202, 202, 255),
    ),
) -> Image.Image:
    canvas = Image.new("RGBA", (width, height), colors[0])
    draw = ImageDraw.Draw(canvas)
    for y in range(0, height, size):
        for x in range(0, width, size):
            if (x // size + y // size) % 2:
                draw.rectangle([x, y, x + size - 1, y + size - 1], fill=colors[1])
    return canvas


def with_checker(image: Image.Image, size: int = 8) -> Image.Image:
    bg = checkerboard(image.width, image.height, size)
    bg.alpha_composite(ensure_rgba(image))
    return bg


def fit_preview(image: Image.Image, size: tuple[int, int], background: str = "checker") -> Image.Image:
    preview = resize_to_fit(ensure_rgba(image), size[0], size[1], "nearest")
    if background == "checker":
        canvas = checkerboard(size[0], size[1])
    else:
        color = parse_color(background)
        canvas = Image.new("RGBA", size, color)
    x = (size[0] - preview.width) // 2
    y = (size[1] - preview.height) // 2
    canvas.alpha_composite(preview, (x, y))
    return canvas


def parse_color(value: str | Sequence[int]) -> tuple[int, int, int, int]:
    if isinstance(value, str):
        text = value.strip().lstrip("#")
        if len(text) == 3:
            text = "".join(c * 2 for c in text)
        if len(text) == 6:
            text += "ff"
        if len(text) != 8:
            raise ValueError(f"Invalid colour {value!r}; use #RGB, #RRGGBB or #RRGGBBAA")
        return (int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16), int(text[6:8], 16))
    vals = list(value)
    while len(vals) < 4:
        vals.append(255)
    return (int(vals[0]), int(vals[1]), int(vals[2]), int(vals[3]))


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def natural_key(value: str) -> list:
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", str(value))]


def frame_paths(folder: str | Path, patterns: Iterable[str] = ("*.png", "*.webp")) -> list[Path]:
    folder = Path(folder)
    files: list[Path] = []
    for pattern in patterns:
        files.extend(folder.glob(pattern))
    return sorted({p.resolve() for p in files if p.is_file()}, key=lambda p: natural_key(p.name))


def image_info(path: str | Path, include_palette: bool = False, max_colors: int = 16) -> dict:
    path = Path(path)
    image = load_image(path, None)
    rgba = image.convert("RGBA")
    info: dict[str, Any] = {
        "path": str(path),
        "filename": path.name,
        "format": image.format,
        "width": image.width,
        "height": image.height,
        "mode": image.mode,
        "is_animated": bool(getattr(image, "is_animated", False)),
        "n_frames": int(getattr(image, "n_frames", 1)),
        "file_size": path.stat().st_size,
        "sha256": sha256_file(path),
        "alpha": alpha_stats(rgba),
    }
    if include_palette:
        info["palette"] = palette(rgba, max_colors=max_colors)
    return info


def label_text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, fill=(20, 20, 20, 255), font=None):
    draw.text(xy, text, fill=fill, font=font)


def default_font(size: int = 14):
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except Exception:
        try:
            return ImageFont.load_default(size=size)
        except TypeError:  # older Pillow
            return ImageFont.load_default()


def write_json(path: str | Path, data, overwrite: bool = True) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite {path}")
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def read_json(path: str | Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
