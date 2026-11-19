"""Prompt-construction tests."""

from __future__ import annotations

import yaml

from sprite_studio.prompting import build_prompt, build_prompt_from_files, negative_prompt


def test_build_prompt_includes_brief_and_style():
    brief = {
        "asset_name": "Moss Slime",
        "asset_category": "character",
        "description": "A small moss-covered slime",
        "canvas_width": 64,
        "canvas_height": 64,
        "transparency_required": True,
        "colour_palette": ["#1b2a2a", "#5f8f5a"],
        "negative_constraints": ["text", "baked shadow"],
    }
    style = {
        "display_name": "Mosslight pixel art",
        "palette": "muted forest greens",
        "generation_prompt_modifiers": ["crisp 1px outline", "limited palette"],
        "negative_prompt_modifiers": ["neon colours"],
        "processing_rules": ["remove chroma background"],
    }
    prompt = build_prompt(brief, style)
    assert "SUBJECT:" in prompt
    assert "Moss Slime" in prompt
    assert "64 x 64 px" in prompt
    assert "Mosslight pixel art" in prompt
    assert "crisp 1px outline" in prompt
    assert "remove chroma background" in prompt
    assert "text" in prompt
    assert prompt.endswith("\n")


def test_negative_prompt_deduplicates_entries():
    brief = {"negative_constraints": ["text", "busy background"]}
    style = {"negative_prompt_modifiers": ["text", "neon colours"]}
    negative = negative_prompt(brief, style)
    assert negative.count("text") == 1
    assert "neon colours" in negative
    assert "watermark" in negative


def test_build_prompt_from_files_writes_output(tmp_path):
    brief = tmp_path / "brief.yaml"
    style = tmp_path / "style.yaml"
    output = tmp_path / "prompt.txt"
    brief.write_text(yaml.safe_dump({"asset_name": "Sparkle", "canvas_width": 32, "canvas_height": 32}), encoding="utf-8")
    style.write_text(yaml.safe_dump({"display_name": "Mosslight"}), encoding="utf-8")
    prompt = build_prompt_from_files(brief, style, output_path=output)
    assert output.read_text(encoding="utf-8") == prompt
    assert "Sparkle" in prompt
