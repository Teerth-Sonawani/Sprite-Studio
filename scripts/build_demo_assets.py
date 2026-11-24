#!/usr/bin/env python
"""Build the Mosslight example project reproducibly.

The art is original procedural demo art drawn with Pillow. It is deliberately
labelled as such: this script proves the processing, QA, manifest and export
pipeline, not the quality of any image-generation provider.

Stages
------
assets   Rebuild raw sources, processed frames, sheets, previews and technical QA.
reviews  Apply `qa/review_decisions.json` to the technical reports.
exports  Build manifests and engine exports from the current reviews.
all      assets -> reviews (when decisions exist) -> exports.

Every generated file is deterministic for the same Pillow build when SOURCE_DATE_EPOCH is set (see sprite_studio/timeutil.py); without it, embedded timestamps use wall-clock time. The script only
removes folders and reports it owns; authored briefs, style guides and animation
specs are never deleted.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sprite_studio.animation import align_frames, make_preview, validate_animation  # noqa: E402
from sprite_studio.background import clean_transparency, remove_background  # noqa: E402
from sprite_studio.export import export_asset  # noqa: E402
from sprite_studio.image_utils import (  # noqa: E402
    load_image,
    save_png,
    sha256_file,
    write_json,
)
from sprite_studio.manifest import build_manifest, validate_manifest  # noqa: E402
from sprite_studio.prompting import build_prompt, negative_prompt  # noqa: E402
from sprite_studio.qa import record_visual_review, validate_sprite  # noqa: E402
from sprite_studio.sheets import build_sheet, contact_sheet  # noqa: E402
from sprite_studio.tiling import assembled_preview, seam_report, wrap_preview  # noqa: E402
from sprite_studio.timeutil import utcnow  # noqa: E402

PROJECT = ROOT / "projects" / "example-project"
BRIEFS = PROJECT / "assets" / "briefs"
SOURCE = PROJECT / "assets" / "source"
PROCEDURAL = SOURCE / "procedural"
PROMPTS = SOURCE / "prompts"
WORKING = PROJECT / "assets" / "working"
APPROVED = PROJECT / "assets" / "approved"
ANIMATIONS = PROJECT / "animations"
QA = PROJECT / "qa"
MANIFESTS = PROJECT / "manifests"
EXPORTS = PROJECT / "exports"
STYLE = PROJECT / "style_guide.yaml"

# Mosslight anchors. No pure black; pure white is limited to emissive cores.
DEEP = (16, 24, 28, 255)          # #10181c
OUTLINE = (27, 42, 42, 255)       # #1b2a2a
SHADOW = (53, 92, 74, 255)        # #355c4a
BASE = (95, 143, 90, 255)         # #5f8f5a
HIGHLIGHT = (168, 198, 108, 255)  # #a8c66c
PAPER = (242, 232, 201, 255)      # #f2e8c9
AMBER = (231, 160, 90, 255)       # #e7a05a
EARTH = (122, 79, 58, 255)        # #7a4f3a
WHITE = (255, 255, 255, 255)      # sparkle core exception
CHROMA = (194, 24, 91, 255)       # disposable key colour for demo sources
TRANSPARENT = (0, 0, 0, 0)

SLIME_SIZE = (64, 64)
SLIME_PIVOT = (32, 60)
VFX_SIZE = (64, 64)
VFX_PIVOT = (32, 32)
ICON_SIZE = (32, 32)
TILE_SIZE = (32, 32)

IDLE_DURATIONS = [160, 160, 160, 160]
WALK_DURATIONS = [100, 100, 100, 100, 100, 100]
VFX_DURATIONS = [80, 80, 70, 70, 90, 110]


def _utcnow() -> str:
    return utcnow()


def _rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _here(path: Path) -> str:
    return path.resolve().relative_to(PROJECT.resolve()).as_posix()


def _new_canvas(size: tuple[int, int], background=TRANSPARENT) -> Image.Image:
    return Image.new("RGBA", size, background)


def _polygon(draw: ImageDraw.ImageDraw, points, fill):
    draw.polygon([(int(x), int(y)) for x, y in points], fill=fill)


def _star_points(cx: int, cy: int, radius: float, inner_ratio: float = 0.30):
    points = []
    for index in range(8):
        angle = math.radians(-90 + index * 45)
        distance = radius if index % 2 == 0 else radius * inner_ratio
        points.append((cx + math.cos(angle) * distance, cy + math.sin(angle) * distance))
    return points


def _diamond(cx: int, cy: int, radius: int):
    return [(cx, cy - radius), (cx + radius, cy), (cx, cy + radius), (cx - radius, cy)]


# --------------------------------------------------------------------------- art
def draw_slime(animation: str, index: int) -> Image.Image:
    """Draw one 64x64 frame on a disposable chroma background."""

    if animation == "idle":
        tops = [20, 22, 19, 21]
        widths = [40, 39, 41, 40]
        fern_shift = [0, 0, -1, 0]
        feet = {
            0: [(17, 28, 54), (35, 46, 54)],
            1: [(17, 28, 54), (35, 46, 54)],
            2: [(17, 28, 54), (35, 46, 54)],
            3: [(17, 28, 54), (35, 46, 54)],
        }
    elif animation == "walk":
        tops = [21, 23, 20, 21, 23, 20]
        widths = [40, 39, 41, 40, 39, 41]
        fern_shift = [0, 1, 2, 0, -1, -2]
        feet = {
            0: [(16, 27, 54), (35, 47, 54)],
            1: [(14, 25, 54), (38, 49, 54)],
            2: [(18, 29, 52), (34, 45, 54)],
            3: [(34, 46, 54), (16, 27, 54)],
            4: [(38, 49, 54), (14, 25, 54)],
            5: [(34, 45, 54), (18, 29, 52)],
        }
    else:
        raise ValueError(f"Unknown slime animation {animation!r}")

    top = tops[index]
    width = widths[index]
    x0 = 32 - width // 2
    x1 = x0 + width - 1
    y1 = 57
    bbox = (x0, top, x1, y1)

    canvas = _new_canvas(SLIME_SIZE, CHROMA)
    draw = ImageDraw.Draw(canvas)

    # Feet sit on the ground line (bottom visible row 59) so alignment keeps the
    # body bob while the pivot stays planted.
    for left, right, foot_top in feet[index]:
        draw.ellipse((left, foot_top, right, 59), fill=BASE, outline=OUTLINE, width=2)

    # Body base, then clipped shading, then a crisp outline.
    mask = Image.new("L", SLIME_SIZE, 0)
    ImageDraw.Draw(mask).ellipse(bbox, fill=255)
    body = _new_canvas(SLIME_SIZE)
    ImageDraw.Draw(body).ellipse(bbox, fill=BASE)

    shadow_layer = _new_canvas(SLIME_SIZE)
    ImageDraw.Draw(shadow_layer).ellipse(
        (x0 + 4, y1 - 14, x1 - 4, y1 - 1), fill=SHADOW
    )
    highlight_layer = _new_canvas(SLIME_SIZE)
    ImageDraw.Draw(highlight_layer).ellipse(
        (x0 + 6, top + 6, x0 + 22, top + 17), fill=HIGHLIGHT
    )
    body = Image.alpha_composite(body, Image.composite(shadow_layer, _new_canvas(SLIME_SIZE), mask))
    body = Image.alpha_composite(body, Image.composite(highlight_layer, _new_canvas(SLIME_SIZE), mask))
    ImageDraw.Draw(body).ellipse(bbox, outline=OUTLINE, width=2)

    # Sparse moss clusters, deliberately clustered rather than single-pixel noise.
    moss = ImageDraw.Draw(body)
    moss.ellipse((x0 + 8, y1 - 13, x0 + 12, y1 - 10), fill=HIGHLIGHT)
    moss.ellipse((x0 + 15, y1 - 9, x0 + 18, y1 - 7), fill=HIGHLIGHT)
    moss.point((x0 + 11, y1 - 15), fill=HIGHLIGHT)

    canvas.alpha_composite(body)

    # Face: eyes stay on the right, following the body top.
    eye_y = top + max(11, (y1 - top) // 3)
    left_eye = x1 - 17
    right_eye = x1 - 8
    for ex in (left_eye, right_eye):
        draw = ImageDraw.Draw(canvas)
        draw.ellipse((ex, eye_y, ex + 5, eye_y + 7), fill=PAPER, outline=OUTLINE, width=1)
        draw.rectangle((ex + 1, eye_y + 2, ex + 3, eye_y + 5), fill=DEEP)
        draw.point((ex + 4, eye_y + 1), fill=WHITE)
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((left_eye + 3, eye_y + 11, left_eye + 10, eye_y + 12), fill=OUTLINE)
    draw.ellipse((x1 - 14, eye_y + 8, x1 - 12, eye_y + 10), fill=AMBER)

    # Fern cluster: three stems with tiny leaves and amber tips.
    shift = fern_shift[index]
    stems = [
        ((31, top + 3), (29 + shift, top - 7)),
        ((32, top + 3), (32 + shift, top - 9)),
        ((34, top + 3), (37 + shift, top - 6)),
    ]
    for start, end in stems:
        draw.line((start, end), fill=OUTLINE, width=3)
        draw.line((start, end), fill=HIGHLIGHT, width=1)
    for end, leaf in zip(
        [stem[1] for stem in stems],
        [(27 + shift, top - 8), (32 + shift, top - 11), (38 + shift, top - 7)],
    ):
        draw.ellipse((leaf[0] - 3, leaf[1] - 2, leaf[0] + 3, leaf[1] + 2), fill=HIGHLIGHT, outline=OUTLINE, width=1)
        draw.point((leaf[0], leaf[1] - 1), fill=AMBER)

    return canvas


def draw_icon() -> Image.Image:
    canvas = _new_canvas(ICON_SIZE, CHROMA)
    draw = ImageDraw.Draw(canvas)
    _polygon(draw, _star_points(16, 16, 13.0, 0.30), SHADOW)
    _polygon(draw, _star_points(16, 16, 11.5, 0.30), AMBER)
    _polygon(draw, _star_points(16, 16, 8.0, 0.38), PAPER)
    _polygon(draw, _diamond(16, 16, 2), WHITE)
    # Two tiny secondary sparkles, kept inside the optical margin.
    for cx, cy in ((7, 8), (25, 23)):
        draw.rectangle((cx - 1, cy, cx + 1, cy), fill=AMBER)
        draw.rectangle((cx, cy - 1, cx, cy + 1), fill=AMBER)
        draw.point((cx, cy), fill=PAPER)
    return canvas


def draw_tile() -> Image.Image:
    size = TILE_SIZE[0]
    canvas = _new_canvas(TILE_SIZE, (BASE[0], BASE[1], BASE[2], 255))
    draw = ImageDraw.Draw(canvas)
    for y in range(size):
        for x in range(size):
            value = (
                0.52
                + 0.20 * math.sin(2 * math.pi * (2 * x + y) / size + 0.4)
                + 0.14 * math.sin(2 * math.pi * (5 * x - 3 * y) / size + 1.1)
                + 0.09 * math.cos(2 * math.pi * 7 * y / size)
            )
            if value < 0.32:
                colour = SHADOW
            elif value < 0.58:
                colour = BASE
            else:
                colour = HIGHLIGHT
            draw.point((x, y), fill=colour)

    # Periodic blades: every copy is drawn at ±tile offsets so the edges wrap.
    for i in range(16):
        bx = (i * 7 + 3) % size
        by = (i * 11 + 5) % size
        length = 1 + (i % 3)
        colour = SHADOW if i % 4 == 0 else HIGHLIGHT
        for ox in (-size, 0, size):
            for oy in (-size, 0, size):
                x = bx + ox
                y = by + oy
                if -2 <= x < size + 2 and -3 <= y < size + 3:
                    draw.line((x, y, x, y + length), fill=colour)

    # Two small flowers, fully interior so they cannot create a seam.
    for cx, cy in ((6, 7), (24, 22)):
        draw.point((cx, cy), fill=AMBER)
        draw.point((cx - 1, cy), fill=PAPER)
        draw.point((cx + 1, cy), fill=PAPER)
        draw.point((cx, cy - 1), fill=PAPER)
        draw.point((cx, cy + 1), fill=PAPER)
    return canvas


def draw_vfx(index: int) -> Image.Image:
    radii = [8, 16, 24, 28, 18, 10]
    radius = radii[index]
    canvas = _new_canvas(VFX_SIZE)
    draw = ImageDraw.Draw(canvas)
    _polygon(draw, _star_points(32, 32, radius + 1.0, 0.28), SHADOW)
    _polygon(draw, _star_points(32, 32, radius, 0.30), AMBER)
    _polygon(draw, _star_points(32, 32, radius * 0.62, 0.36), PAPER)
    core = max(1, round(radius * 0.10))
    _polygon(draw, _diamond(32, 32, core), WHITE)

    satellite_count = 4 if radius >= 18 else 2
    for i in range(satellite_count):
        angle = math.radians(22 + i * 97 + index * 17)
        distance = min(26, radius + 6)
        sx = int(round(32 + math.cos(angle) * distance))
        sy = int(round(32 + math.sin(angle) * distance))
        sat = 2 if radius >= 18 else 1
        if not (2 <= sx - sat and sx + sat <= 61 and 2 <= sy - sat and sy + sat <= 61):
            continue
        _polygon(draw, _diamond(sx, sy, sat), AMBER if i % 2 == 0 else HIGHLIGHT)
    return canvas


# --------------------------------------------------------------------- pipeline
def reset_generated(stage: str) -> None:
    """Remove only the outputs that `stage` regenerates.

    `assets` owns working frames, approved frames, source prompts and technical
    reports.  It deliberately does **not** touch `exports/` or `manifests/`, so
    running the assets stage alone cannot destroy a previously exported build.
    `exports` owns the manifests and export folders.

    Authored inputs are never removed: briefs, style guides, animation specs and
    `qa/review_decisions.json` live outside these folders.
    """

    if stage == "exports":
        folders = (MANIFESTS, EXPORTS)
    else:
        folders = (WORKING, APPROVED, QA / "processing", PROMPTS, PROCEDURAL)

    for folder in folders:
        if folder.exists():
            shutil.rmtree(folder)

    if stage != "exports":
        for pattern in ("*_technical.json", "*_animation.json", "*_review.json"):
            for path in QA.glob(pattern):
                path.unlink()


def _processing_report(
    asset_id: str,
    source_paths: list[Path],
    working_paths: list[Path],
    removal_reports: list[dict],
    clean_reports: list[dict],
) -> None:
    write_json(
        QA / "processing" / f"{asset_id}_processing.json",
        {
            "asset_id": asset_id,
            "generated_at": _utcnow(),
            "source_mode": "procedural chroma or native alpha",
            "sources": [_rel(p) for p in source_paths],
            "working_outputs": [_rel(p) for p in working_paths],
            "background_removal": removal_reports,
            "transparency_cleanup": clean_reports,
        },
    )


def process_slime() -> dict:
    source_dir = PROCEDURAL / "moss_slime"
    working_dir = WORKING / "moss_slime"
    approved_dir = APPROVED / "moss_slime"
    for animation in ("idle", "walk"):
        (source_dir / animation).mkdir(parents=True, exist_ok=True)
        (working_dir / animation).mkdir(parents=True, exist_ok=True)
        (approved_dir / "frames" / animation).mkdir(parents=True, exist_ok=True)

    processing = {}
    for animation, count, durations in (
        ("idle", 4, IDLE_DURATIONS),
        ("walk", 6, WALK_DURATIONS),
    ):
        sources, working, removals, cleans = [], [], [], []
        frames = []
        for index in range(count):
            raw = draw_slime(animation, index)
            src_path = source_dir / animation / f"moss_slime__{animation}__source_{index:03d}.png"
            save_png(raw, src_path, overwrite=True)
            sources.append(src_path)

            removed, removal = remove_background(raw, tolerance=28, border=2, method="edge")
            cleaned, clean = clean_transparency(removed, min_island=2, preserve_largest=True)
            work_path = working_dir / animation / f"moss_slime__{animation}__frame_{index:03d}.png"
            save_png(cleaned, work_path, overwrite=True)
            working.append(work_path)
            removals.append(removal)
            cleans.append(clean)
            frames.append(cleaned)

        aligned, alignment = align_frames(
            frames,
            canvas_width=64,
            canvas_height=64,
            pivot_x=32,
            pivot_y=60,
            align="bottom-center",
            align_y=True,
            resample="nearest",
        )
        final_paths = []
        for index, frame in enumerate(aligned):
            out = approved_dir / "frames" / animation / f"moss_slime__{animation}__frame_{index:03d}.png"
            save_png(frame, out, overwrite=True)
            final_paths.append(out)

        processing[animation] = {
            "frames": final_paths,
            "durations": durations,
            "alignment": alignment,
        }
        _processing_report(
            f"moss_slime_{animation}",
            sources,
            working,
            removals,
            cleans,
        )

    return processing


def process_icon() -> Path:
    source = draw_icon()
    src_path = PROCEDURAL / "ui_sparkle" / "ui_sparkle__source.png"
    save_png(source, src_path, overwrite=True)
    removed, removal = remove_background(source, tolerance=28, border=2, method="edge")
    cleaned, clean = clean_transparency(removed, min_island=2, preserve_largest=True)
    work_path = WORKING / "ui_sparkle" / "ui_sparkle.png"
    save_png(cleaned, work_path, overwrite=True)
    out = APPROVED / "ui_sparkle" / "frames" / "ui_sparkle.png"
    save_png(cleaned, out, overwrite=True)
    _processing_report("ui_sparkle", [src_path], [work_path], [removal], [clean])
    return out


def process_tile() -> Path:
    source = draw_tile()
    src_path = PROCEDURAL / "grass_tile" / "grass_tile__source.png"
    save_png(source, src_path, overwrite=True)
    work_path = WORKING / "grass_tile" / "grass_tile.png"
    save_png(source, work_path, overwrite=True)
    out = APPROVED / "grass_tile" / "frames" / "grass_tile.png"
    save_png(source, out, overwrite=True)
    write_json(
        QA / "processing" / "grass_tile_processing.json",
        {
            "asset_id": "grass_tile",
            "generated_at": _utcnow(),
            "method": "periodic analytic pattern plus wrapped blade copies",
            "source": _rel(src_path),
            "output": _rel(out),
        },
    )
    return out


def process_vfx() -> dict:
    source_dir = PROCEDURAL / "sparkle_vfx"
    working_dir = WORKING / "sparkle_vfx"
    approved_dir = APPROVED / "sparkle_vfx"
    (approved_dir / "frames").mkdir(parents=True, exist_ok=True)
    sources, working, removals, cleans, frames = [], [], [], [], []
    for index in range(6):
        raw = draw_vfx(index)
        src_path = source_dir / f"sparkle_vfx__burst__source_{index:03d}.png"
        save_png(raw, src_path, overwrite=True)
        sources.append(src_path)
        cleaned, clean = clean_transparency(raw, min_island=2, preserve_largest=True)
        work_path = working_dir / f"sparkle_vfx__burst__frame_{index:03d}.png"
        save_png(cleaned, work_path, overwrite=True)
        working.append(work_path)
        removals.append({"method": "none", "reason": "source authored with native alpha"})
        cleans.append(clean)
        frames.append(cleaned)

    aligned, alignment = align_frames(
        frames,
        canvas_width=64,
        canvas_height=64,
        pivot_x=32,
        pivot_y=32,
        align="none",
        align_y=True,
        resample="nearest",
    )
    final_paths = []
    for index, frame in enumerate(aligned):
        out = approved_dir / "frames" / f"sparkle_vfx__burst__frame_{index:03d}.png"
        save_png(frame, out, overwrite=True)
        final_paths.append(out)
    _processing_report("sparkle_vfx", sources, working, removals, cleans)
    return {"frames": final_paths, "durations": VFX_DURATIONS, "alignment": alignment}


def build_sheets(processing: dict, vfx: dict) -> dict:
    sheets = {}
    for asset_id, animation, count, durations in (
        ("moss_slime", "idle", 4, IDLE_DURATIONS),
        ("moss_slime", "walk", 6, WALK_DURATIONS),
    ):
        frames = [load_image(p) for p in processing[animation]["frames"]]
        sheet, meta = build_sheet(
            frames,
            layout="horizontal",
            cell_width=64,
            cell_height=64,
            spacing=0,
            margin=0,
            durations=durations,
            metadata={"animation_id": f"{asset_id}_{animation}", "asset_id": asset_id, "animation": animation},
        )
        sheet_path = APPROVED / asset_id / "spritesheets" / f"{asset_id}__{animation}__sheet.png"
        save_png(sheet, sheet_path, overwrite=True)
        sidecar = sheet_path.with_suffix(".json")
        write_json(sidecar, meta)
        sheets[f"{asset_id}_{animation}"] = {"sheet": sheet_path, "metadata": sidecar}

    frames = [load_image(p) for p in vfx["frames"]]
    sheet, meta = build_sheet(
        frames,
        layout="horizontal",
        cell_width=64,
        cell_height=64,
        spacing=0,
        margin=0,
        durations=VFX_DURATIONS,
        metadata={"animation_id": "sparkle_vfx_burst", "asset_id": "sparkle_vfx", "animation": "burst"},
    )
    sheet_path = APPROVED / "sparkle_vfx" / "spritesheets" / "sparkle_vfx__burst__sheet.png"
    save_png(sheet, sheet_path, overwrite=True)
    sidecar = sheet_path.with_suffix(".json")
    write_json(sidecar, meta)
    sheets["sparkle_vfx_burst"] = {"sheet": sheet_path, "metadata": sidecar}
    return sheets


def build_previews(processing: dict, vfx: dict, tile: Path, icon: Path) -> dict:
    outputs = {}

    idle_frames = [load_image(p) for p in processing["idle"]["frames"]]
    idle_dir = APPROVED / "moss_slime" / "previews"
    idle_gif = idle_dir / "moss_slime__idle__preview.gif"
    make_preview(
        idle_frames,
        idle_gif,
        durations=IDLE_DURATIONS,
        background="checker",
        scale=2,
        overwrite=True,
        title="moss_slime idle (4 frames, 6 fps)",
    )
    idle_apng = idle_dir / "moss_slime__idle__preview.png"
    make_preview(
        idle_frames,
        idle_apng,
        durations=IDLE_DURATIONS,
        background="transparent",
        scale=2,
        overwrite=True,
    )
    idle_contact = idle_dir / "moss_slime__idle__contact.png"
    save_png(
        contact_sheet(
            [p for p in processing["idle"]["frames"]],
            columns=4,
            title="moss_slime idle",
        ),
        idle_contact,
        overwrite=True,
    )
    outputs["moss_slime_idle"] = [idle_gif, idle_apng, idle_contact]

    walk_frames = [load_image(p) for p in processing["walk"]["frames"]]
    walk_dir = APPROVED / "moss_slime" / "previews"
    walk_gif = walk_dir / "moss_slime__walk__preview.gif"
    make_preview(
        walk_frames,
        walk_gif,
        durations=WALK_DURATIONS,
        background="checker",
        scale=2,
        overwrite=True,
        title="moss_slime walk (6 frames, 10 fps)",
    )
    walk_webp = walk_dir / "moss_slime__walk__preview.webp"
    make_preview(
        walk_frames,
        walk_webp,
        durations=WALK_DURATIONS,
        background="transparent",
        scale=2,
        overwrite=True,
    )
    walk_contact = walk_dir / "moss_slime__walk__contact.png"
    save_png(
        contact_sheet(
            [p for p in processing["walk"]["frames"]],
            columns=6,
            title="moss_slime walk",
        ),
        walk_contact,
        overwrite=True,
    )
    mp4_note = None
    try:
        walk_mp4 = walk_dir / "moss_slime__walk__preview.mp4"
        make_preview(
            walk_frames,
            walk_mp4,
            durations=WALK_DURATIONS,
            background="#10181c",
            scale=2,
            overwrite=True,
        )
        outputs["moss_slime_walk"] = [walk_gif, walk_webp, walk_contact, walk_mp4]
    except Exception as exc:  # optional dependency; keep the build honest
        mp4_note = f"MP4 preview skipped: {exc}"
        outputs["moss_slime_walk"] = [walk_gif, walk_webp, walk_contact]

    vfx_frames = [load_image(p) for p in vfx["frames"]]
    vfx_dir = APPROVED / "sparkle_vfx" / "previews"
    vfx_webp = vfx_dir / "sparkle_vfx__burst__preview.webp"
    make_preview(
        vfx_frames,
        vfx_webp,
        durations=VFX_DURATIONS,
        background="transparent",
        scale=2,
        overwrite=True,
    )
    vfx_gif = vfx_dir / "sparkle_vfx__burst__preview.gif"
    make_preview(
        vfx_frames,
        vfx_gif,
        durations=VFX_DURATIONS,
        background="checker",
        scale=2,
        overwrite=True,
        title="sparkle_vfx burst (6 frames, 12 fps)",
    )
    vfx_contact = vfx_dir / "sparkle_vfx__burst__contact.png"
    save_png(
        contact_sheet([p for p in vfx["frames"]], columns=6, title="sparkle_vfx burst"),
        vfx_contact,
        overwrite=True,
    )
    outputs["sparkle_vfx_burst"] = [vfx_webp, vfx_gif, vfx_contact]

    tile_image = load_image(tile)
    tile_dir = APPROVED / "grass_tile" / "previews"
    tile_assembled = tile_dir / "grass_tile__assembled.png"
    save_png(assembled_preview(tile_image, grid=3, background="checker"), tile_assembled, overwrite=True)
    tile_wrap = tile_dir / "grass_tile__wrap_2x2.png"
    save_png(wrap_preview(tile_image, 2), tile_wrap, overwrite=True)
    outputs["grass_tile"] = [tile_assembled, tile_wrap]

    icon_image = load_image(icon)
    icon_dir = APPROVED / "ui_sparkle" / "previews"
    icon_contact = icon_dir / "ui_sparkle__contact.png"
    save_png(contact_sheet([icon_image], columns=1, title="ui_sparkle 32x32"), icon_contact, overwrite=True)
    outputs["ui_sparkle"] = [icon_contact]

    if mp4_note:
        write_json(QA / "preview_notes.json", {"note": mp4_note, "generated_at": _utcnow()})
    return outputs


def build_prompts() -> dict:
    prompts = {}
    for brief_name in ("moss_slime", "grass_tile", "ui_sparkle", "sparkle_vfx"):
        brief_path = BRIEFS / f"{brief_name}.yaml"
        from sprite_studio.manifest import _load_structured

        brief = _load_structured(brief_path)
        style = _load_structured(STYLE)
        prompt = build_prompt(brief, style)
        negative = negative_prompt(brief, style)
        out = PROMPTS / f"{brief_name}.prompt.txt"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(prompt, encoding="utf-8")
        (PROMPTS / f"{brief_name}.negative.txt").write_text(negative + "\n", encoding="utf-8")
        prompts[brief_name] = out
    (PROMPTS / "README.md").write_text(
        "# Demo Prompts\n\n"
        "These prompts were produced by `tools/build_prompt.py` from the sample\n"
        "briefs and frozen style guide. They are **not** evidence of AI generation:\n"
        "the checked-in demo art is original procedural Pillow art. The prompts show\n"
        "the handoff a real provider run would receive.\n",
        encoding="utf-8",
    )
    return prompts


def _frame_spec(size: tuple[int, int], pivot: tuple[int, int], padding: int = 2) -> dict:
    return {
        "width": size[0],
        "height": size[1],
        "mode": "RGBA",
        "transparency_required": True,
        "padding": padding,
        "pivot": {"x": pivot[0], "y": pivot[1]},
        "allow_edge_contact": False,
    }


def _aggregate_report(
    asset_id: str,
    frame_paths: list[Path],
    animation_reports: dict | None = None,
    extra_checks: list[dict] | None = None,
) -> dict:
    frame_reports = []
    critical = []
    warnings = []
    for path in frame_paths:
        report = validate_sprite(path, _frame_spec(load_image(path).size, _pivot_for(asset_id)))
        frame_reports.append(
            {
                "path": _rel(path),
                "technical_status": report["technical_status"],
                "critical_failures": report["critical_failures"],
                "warnings": report["warnings"],
                "checks": report["checks"],
                "stats": report.get("stats"),
                "sha256": report.get("sha256"),
            }
        )
        critical.extend(f"{path.name}:{name}" for name in report["critical_failures"])
        warnings.extend(f"{path.name}:{name}" for name in report["warnings"])

    animation_reports = animation_reports or {}
    animation_failures = [
        name for name, result in animation_reports.items() if result.get("status") == "FAIL"
    ]
    for name, result in animation_reports.items():
        warnings.extend(f"{name}:{warning}" for warning in result.get("warnings", []))

    checks = [
        {
            "name": "frame_technical_checks",
            "ok": not critical,
            "severity": "critical",
            "detail": f"{len(frame_reports)} frame report(s); {len(critical)} critical failure(s)",
        },
        {
            "name": "animation_checks",
            "ok": not animation_failures,
            "severity": "critical",
            "detail": f"{len(animation_reports)} animation report(s); failures: {animation_failures}",
        },
    ]
    checks.extend(extra_checks or [])
    technical_status = "REJECTED" if (critical or animation_failures or any(not c["ok"] for c in (extra_checks or []) if c.get("severity") == "critical")) else "TECHNICAL_PASS"
    return {
        "asset": asset_id,
        "generated_at": _utcnow(),
        "technical_status": technical_status,
        "visual_status": "NOT_REVIEWED",
        "qa_status": technical_status,
        "checks": checks,
        "critical_failures": critical,
        "warnings": sorted(set(warnings)),
        "frame_reports": frame_reports,
        "animation_reports": animation_reports,
        "human_approved": False,
        "human_approved_at": None,
        "note": (
            "Technical checks only. APPROVED requires a separate evidence-backed visual review. "
            "AI review is scoped to demo/internal use."
        ),
    }


def _pivot_for(asset_id: str) -> tuple[int, int]:
    if asset_id in {"moss_slime", "slime"}:
        return SLIME_PIVOT
    if asset_id == "sparkle_vfx":
        return VFX_PIVOT
    if asset_id == "ui_sparkle":
        return (16, 16)
    return (16, 16)


def run_technical_qa(processing: dict, vfx: dict, tile: Path, icon: Path) -> dict:
    anime = {}

    idle_frames = [load_image(p) for p in processing["idle"]["frames"]]
    idle = validate_animation(
        idle_frames,
        expected_count=4,
        expected_size=(64, 64),
        pivot=SLIME_PIVOT,
        loop=True,
        durations=IDLE_DURATIONS,
    )
    anime["moss_slime_idle"] = idle

    walk_frames = [load_image(p) for p in processing["walk"]["frames"]]
    walk = validate_animation(
        walk_frames,
        expected_count=6,
        expected_size=(64, 64),
        pivot=SLIME_PIVOT,
        loop=True,
        durations=WALK_DURATIONS,
    )
    anime["moss_slime_walk"] = walk

    vfx_frames = [load_image(p) for p in vfx["frames"]]
    vfx_result = validate_animation(
        vfx_frames,
        expected_count=6,
        expected_size=(64, 64),
        pivot=VFX_PIVOT,
        loop=False,
        durations=VFX_DURATIONS,
        max_scale_variation=0.80,
        max_palette_drift=45.0,
    )
    anime["sparkle_vfx_burst"] = vfx_result

    for name, result in anime.items():
        write_json(QA / f"{name}_animation.json", result)

    slime_frames = processing["idle"]["frames"] + processing["walk"]["frames"]
    slime_report = _aggregate_report(
        "moss_slime",
        slime_frames,
        {"moss_slime_idle": idle, "moss_slime_walk": walk},
    )
    write_json(QA / "moss_slime_technical.json", slime_report)

    vfx_report = _aggregate_report("sparkle_vfx", vfx["frames"], {"sparkle_vfx_burst": vfx_result})
    write_json(QA / "sparkle_vfx_technical.json", vfx_report)

    tile_report = validate_sprite(
        tile,
        {
            "width": 32,
            "height": 32,
            "mode": "RGBA",
            "transparency_required": False,
            "padding": 0,
            "allow_edge_contact": True,
        },
    )
    seam = seam_report(load_image(tile))
    tile_report["technical_status"] = (
        "REJECTED" if tile_report["technical_status"] == "REJECTED" or seam["status"] == "WARN" else "TECHNICAL_PASS"
    )
    tile_report["qa_status"] = tile_report["technical_status"]
    tile_report["seam"] = seam
    tile_report["checks"].append(
        {
            "name": "tile_seam",
            "ok": seam["status"] == "PASS",
            "severity": "critical",
            "detail": f"seam report {seam['status']}",
        }
    )
    write_json(QA / "grass_tile_technical.json", tile_report)

    icon_report = validate_sprite(icon, _frame_spec(ICON_SIZE, (16, 16)))
    write_json(QA / "ui_sparkle_technical.json", icon_report)

    return {
        "moss_slime": slime_report,
        "sparkle_vfx": vfx_report,
        "grass_tile": tile_report,
        "ui_sparkle": icon_report,
    }


def apply_reviews() -> dict:
    decisions_path = QA / "review_decisions.json"
    if not decisions_path.is_file():
        raise FileNotFoundError(
            f"No review decisions at {decisions_path}. Inspect the generated evidence, then create the file."
        )
    decisions = json.loads(decisions_path.read_text(encoding="utf-8"))
    results = {}
    for asset_id, decision in decisions.get("assets", {}).items():
        technical_path = QA / f"{asset_id}_technical.json"
        if not technical_path.is_file():
            raise FileNotFoundError(f"Technical report missing for {asset_id}: {technical_path}")
        technical = json.loads(technical_path.read_text(encoding="utf-8"))
        evidence = decision.get("evidence", [])
        for item in evidence:
            if not (ROOT / item).is_file():
                raise FileNotFoundError(f"Review evidence does not exist: {item}")
        review = record_visual_review(
            technical,
            decision=decision.get("decision", "revise"),
            reviewer=decision.get("reviewer", "OpenCode agent"),
            reviewer_type=decision.get("reviewer_type", "ai_agent"),
            notes=decision.get("notes", ""),
            scores=decision.get("scores", {}),
            evidence=evidence,
            evidence_root=ROOT,
        )
        out = QA / f"{asset_id}_review.json"
        write_json(out, review)
        results[asset_id] = review
    return results


def _provenance(asset_id: str, source_files: list[Path]) -> dict:
    return {
        "provider": "scripted_pillow",
        "mode": "procedural_demo",
        "model_key": None,
        "generation_id": None,
        "prompt": None,
        "prompt_file": _here(PROMPTS / f"{asset_id}.prompt.txt")
        if (PROMPTS / f"{asset_id}.prompt.txt").is_file()
        else None,
        "source_files": [_rel(p) for p in source_files],
        "license": "MIT (original procedural demo art for this workspace)",
        "notes": (
            "Original procedural demo art drawn by scripts/build_demo_assets.py. "
            "Not AI-generated and not a provider quality showcase."
        ),
    }


def _asset_sources(asset_id: str) -> list[Path]:
    if asset_id == "moss_slime":
        folder = PROCEDURAL / "moss_slime"
    else:
        folder = PROCEDURAL / asset_id
    if not folder.is_dir():
        return []
    return sorted(folder.rglob("*.png"))


def build_manifest_for(
    asset_id: str,
    asset_dir: Path,
    brief: Path,
    animations_dir: Path | None,
    review: dict | None,
) -> dict:
    manifest_path = MANIFESTS / f"{asset_id}.manifest.json"
    qa_path = QA / f"{asset_id}_review.json" if review else QA / f"{asset_id}_technical.json"
    manifest = build_manifest(
        asset_dir,
        brief_path=brief,
        style_path=STYLE,
        animations_dir=animations_dir,
        qa_report_path=qa_path,
        provenance=_provenance(asset_id, _asset_sources(asset_id)),
        output_path=None,
        path_base=manifest_path.parent,
    )
    schema = ROOT / "schemas" / "asset_manifest.schema.json"
    ok, errors = validate_manifest(manifest, schema)
    manifest["validation"] = {"schema": _rel(schema), "ok": ok, "errors": errors}
    write_json(manifest_path, manifest)
    return manifest


def build_exports(reviews: dict) -> dict:
    summary = {"generated_at": _utcnow(), "assets": {}, "exports": {}}
    # Exports own the manifests and export folders; rebuild both from scratch so
    # stale manifests for removed assets cannot survive.
    reset_generated("exports")
    MANIFESTS.mkdir(parents=True, exist_ok=True)

    definitions = [
        ("moss_slime", APPROVED / "moss_slime", BRIEFS / "moss_slime.yaml", ANIMATIONS),
        ("grass_tile", APPROVED / "grass_tile", BRIEFS / "grass_tile.yaml", None),
        ("ui_sparkle", APPROVED / "ui_sparkle", BRIEFS / "ui_sparkle.yaml", None),
        ("sparkle_vfx", APPROVED / "sparkle_vfx", BRIEFS / "sparkle_vfx.yaml", ANIMATIONS),
    ]
    manifests = {}
    for asset_id, asset_dir, brief, animations_dir in definitions:
        manifest = build_manifest_for(asset_id, asset_dir, brief, animations_dir, reviews.get(asset_id))
        manifests[asset_id] = manifest
        summary["assets"][asset_id] = {
            "manifest": _rel(MANIFESTS / f"{asset_id}.manifest.json"),
            "qa_status": manifest["qa"]["qa_status"],
            "human_approved": manifest["qa"]["human_approved"],
            "frame_count": len(manifest["files"].get("frame", [])),
            "sheet_count": len(manifest["files"].get("sheet", [])),
            "preview_count": len(manifest["files"].get("preview", [])),
            "validation_ok": manifest["validation"]["ok"],
        }

    # Remove generated export folders before writing so the script is idempotent.
    EXPORTS.mkdir(parents=True, exist_ok=True)

    jobs = [
        ("moss_slime", "generic_png", EXPORTS / "generic" / "moss_slime"),
        ("moss_slime", "godot_4", EXPORTS / "godot"),
        ("moss_slime", "unity_2022", EXPORTS / "unity"),
        ("grass_tile", "generic_png", EXPORTS / "generic" / "grass_tile"),
        ("ui_sparkle", "generic_png", EXPORTS / "generic" / "ui_sparkle"),
        ("sparkle_vfx", "generic_png", EXPORTS / "generic" / "sparkle_vfx"),
    ]
    for asset_id, profile, out_dir in jobs:
        manifest = manifests[asset_id]
        if manifest["qa"]["qa_status"] != "APPROVED":
            summary["exports"][f"{asset_id}:{profile}"] = {
                "skipped": True,
                "reason": f"qa_status is {manifest['qa']['qa_status']}, not APPROVED",
            }
            continue
        result = export_asset(
            manifest,
            MANIFESTS / f"{asset_id}.manifest.json",
            profile,
            out_dir,
            force=True,
        )
        summary["exports"][f"{asset_id}:{profile}"] = {
            "profile": result["profile"],
            "output_dir": _rel(Path(result["output_dir"])),
            "files": [_rel(Path(p)) for p in result["files"]],
        }

    # Convenience copies for the quick-start examples.
    preview_dir = EXPORTS / "previews"
    preview_dir.mkdir(parents=True, exist_ok=True)
    copies = [
        (APPROVED / "moss_slime" / "previews" / "moss_slime__idle__preview.gif", "moss_slime_idle.gif"),
        (APPROVED / "moss_slime" / "previews" / "moss_slime__walk__preview.gif", "moss_slime_walk.gif"),
        (APPROVED / "sparkle_vfx" / "previews" / "sparkle_vfx__burst__preview.gif", "sparkle_vfx_burst.gif"),
    ]
    for source, name in copies:
        if source.is_file():
            shutil.copy2(source, preview_dir / name)

    # Verify every manifest file hash against the current bytes.
    verification = {"ok": True, "checked": 0, "errors": []}
    for asset_id, manifest in manifests.items():
        manifest_path = MANIFESTS / f"{asset_id}.manifest.json"
        for role, records in manifest["files"].items():
            for record in records:
                path = (manifest_path.parent / record["path"]).resolve()
                if not path.is_file():
                    verification["ok"] = False
                    verification["errors"].append(f"{asset_id}: missing {record['path']}")
                    continue
                if sha256_file(path) != record["sha256"]:
                    verification["ok"] = False
                    verification["errors"].append(f"{asset_id}: hash mismatch {record['path']}")
                verification["checked"] += 1
    summary["verification"] = verification
    summary["note"] = (
        "Demo art is procedural Pillow art, not AI-generated. AI visual reviews are "
        "scoped to demo_or_internal and keep human_approved=false."
    )
    write_json(MANIFESTS / "build_summary.json", summary)
    write_json(QA / "pipeline_summary.json", summary)
    return summary


def build_assets() -> dict:
    reset_generated("assets")
    for folder in (PROCEDURAL, PROMPTS, WORKING, APPROVED, QA / "processing", MANIFESTS, EXPORTS):
        folder.mkdir(parents=True, exist_ok=True)

    prompts = build_prompts()
    processing = process_slime()
    vfx = process_vfx()
    tile = process_tile()
    icon = process_icon()
    sheets = build_sheets(processing, vfx)
    previews = build_previews(processing, vfx, tile, icon)
    technical = run_technical_qa(processing, vfx, tile, icon)

    summary = {
        "generated_at": _utcnow(),
        "stage": "assets",
        "prompts": {k: _rel(v) for k, v in prompts.items()},
        "sheets": {k: _rel(v["sheet"]) for k, v in sheets.items()},
        "previews": {k: [_rel(p) for p in v] for k, v in previews.items()},
        "technical_status": {k: v["technical_status"] for k, v in technical.items()},
        "note": "Procedural demo art; not AI-generated.",
    }
    write_json(QA / "assets_stage_summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--stage",
        choices=["assets", "reviews", "exports", "all"],
        default="all",
        help="Pipeline stage to run (default: all)",
    )
    args = parser.parse_args()

    if args.stage in {"assets", "all"}:
        summary = build_assets()
        print("Assets rebuilt.")
        for asset, status in summary["technical_status"].items():
            print(f"  {asset}: {status}")
    if args.stage in {"reviews", "all"}:
        if (QA / "review_decisions.json").is_file():
            reviews = apply_reviews()
            print(f"Applied {len(reviews)} visual review(s).")
        elif args.stage == "reviews":
            raise FileNotFoundError(f"Missing {QA / 'review_decisions.json'}")
        else:
            reviews = {}
            print("No review decisions yet; skipping visual review.")
    if args.stage in {"exports", "all"}:
        if not (QA / "review_decisions.json").is_file() and args.stage == "exports":
            raise FileNotFoundError(f"Missing {QA / 'review_decisions.json'}")
        reviews = {}
        for asset_id in ("moss_slime", "grass_tile", "ui_sparkle", "sparkle_vfx"):
            path = QA / f"{asset_id}_review.json"
            if path.is_file():
                reviews[asset_id] = json.loads(path.read_text(encoding="utf-8"))
        summary = build_exports(reviews)
        print("Exports built.")
        for name, result in summary["exports"].items():
            if result.get("skipped"):
                print(f"  {name}: SKIPPED ({result['reason']})")
            else:
                print(f"  {name}: {result['output_dir']}")
        print(f"  manifest hash verification: {'PASS' if summary['verification']['ok'] else 'FAIL'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
