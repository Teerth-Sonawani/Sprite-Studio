"""Shared pytest fixtures and path setup for the 2D Sprite Studio tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def make_frame(size: tuple[int, int] = (16, 16), offset: int = 0, colour=(80, 140, 90, 255)) -> Image.Image:
    """A small opaque subject with transparent margins and a readable eye."""

    image = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((3, 5 + offset, 12, 13 + offset), fill=colour, outline=(20, 30, 30, 255))
    draw.rectangle((6, 8 + offset, 7, 9 + offset), fill=(240, 230, 200, 255))
    return image


@pytest.fixture
def frame() -> Image.Image:
    image = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    ImageDraw.Draw(image).rectangle((4, 4, 11, 11), fill=(80, 140, 90, 255))
    return image


@pytest.fixture
def frames() -> list[Image.Image]:
    return [make_frame(offset=index % 2) for index in range(4)]


@pytest.fixture
def root() -> Path:
    return ROOT


@pytest.fixture
def demo_asset(tmp_path):
    """A complete, approved miniature asset with sheet, sidecar and GIF preview."""

    import json

    from sprite_studio.animation import make_preview
    from sprite_studio.image_utils import save_png, write_json
    from sprite_studio.manifest import build_manifest
    from sprite_studio.qa import record_visual_review, validate_sprite
    from sprite_studio.sheets import build_sheet

    asset_dir = tmp_path / "assets" / "approved" / "demo"
    frames_dir = asset_dir / "frames"
    sheet_dir = asset_dir / "spritesheets"
    preview_dir = asset_dir / "previews"
    for folder in (frames_dir, sheet_dir, preview_dir):
        folder.mkdir(parents=True, exist_ok=True)

    frames = [make_frame(offset=index % 2) for index in range(2)]
    frame_paths = []
    for index, frame in enumerate(frames):
        path = frames_dir / f"demo__idle__frame_{index:03d}.png"
        save_png(frame, path)
        frame_paths.append(path)

    sheet, meta = build_sheet(frames, layout="horizontal", cell_width=16, cell_height=16, durations=[100, 100])
    sheet_path = sheet_dir / "demo__idle__sheet.png"
    save_png(sheet, sheet_path)
    meta.update({"asset_id": "demo", "animation": "idle", "animation_id": "demo_idle"})
    write_json(sheet_path.with_suffix(".json"), meta)

    preview_path = preview_dir / "demo__idle__contact.png"
    save_png(frames[0], preview_path)
    make_preview(frames, preview_dir / "demo__idle__preview.gif", durations=[100, 100], background="checker")

    brief = tmp_path / "demo.brief.yaml"
    brief.write_text(
        "\n".join(
            [
                "asset_id: demo",
                "asset_name: Demo Sprite",
                "asset_category: character",
                "canvas_width: 16",
                "canvas_height: 16",
                "pivot: {x: 8, y: 15}",
                "anchor_point: bottom-center",
                "target_engine: generic",
                "license: MIT (test fixture)",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    style = tmp_path / "demo.style.yaml"
    style.write_text("style_id: demo_style\npalette: ['#1b2a2a', '#5f8f5a']\n", encoding="utf-8")

    animations = tmp_path / "animations"
    animations.mkdir()
    (animations / "demo_idle.yaml").write_text(
        "\n".join(
            [
                "animation_id: demo_idle",
                "asset_id: demo",
                "animation_name: idle",
                "frame_count: 2",
                "frame_rate: 10",
                "loop: true",
                "sheet: demo__idle__sheet.png",
                "frame_sequence:",
                "  - frame: 0",
                "    duration_ms: 100",
                "  - frame: 1",
                "    duration_ms: 100",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    technical = validate_sprite(
        frame_paths[0],
        {
            "width": 16,
            "height": 16,
            "mode": "RGBA",
            "transparency_required": True,
            "padding": 2,
            "pivot": {"x": 8, "y": 15},
        },
    )
    assert technical["technical_status"] == "TECHNICAL_PASS"
    review = record_visual_review(
        technical,
        decision="approve",
        reviewer="unit-test reviewer",
        reviewer_type="ai_agent",
        notes="Fixture approval for export tests; demo scope only.",
        scores={"silhouette": 5},
        evidence=[str(preview_path)],
    )
    qa_dir = tmp_path / "qa"
    review_path = qa_dir / "demo_review.json"
    write_json(review_path, review)

    manifest_dir = tmp_path / "manifests"
    manifest_path = manifest_dir / "demo.manifest.json"
    manifest = build_manifest(
        asset_dir,
        brief_path=brief,
        style_path=style,
        animations_dir=animations,
        qa_report_path=review_path,
        provenance={
            "provider": "unit-test",
            "mode": "fixture",
            "model_key": None,
            "generation_id": None,
            "prompt": None,
            "source_files": [],
            "license": "MIT (test fixture)",
            "notes": "Tiny approved fixture used by the test suite.",
        },
        path_base=manifest_dir,
    )
    write_json(manifest_path, manifest)

    return {
        "asset_dir": asset_dir,
        "manifest": manifest,
        "manifest_path": manifest_path,
        "review_path": review_path,
        "frame_paths": frame_paths,
        "frame": frames[0],
        "sheet_path": sheet_path,
        "preview_path": preview_path,
        "brief_path": brief,
        "style_path": style,
        "animations_dir": animations,
    }
