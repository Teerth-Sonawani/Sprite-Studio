"""Prompt construction from structured asset briefs and style profiles.

The prompt is assembled in stable sections so a reviewer can see exactly which
requirement produced each line.  It does not attempt to hide the limitations of
image generators: exact dimensions, transparency and sprite-sheet grids must
still be verified after generation.
"""

from __future__ import annotations

from pathlib import Path

import yaml


def _load(path: str | Path | None) -> dict:
    if not path:
        return {}
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")
    if path.suffix.lower() in {".yaml", ".yml"}:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    elif path.suffix.lower() == ".json":
        import json

        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        raise ValueError("Brief/style must be .yaml, .yml or .json")
    if not isinstance(data, dict):
        raise ValueError(f"Expected a mapping in {path}")
    return data


def _value(data: dict, *keys, default=""):
    for key in keys:
        if key in data and data[key] not in (None, "", []):
            return data[key]
    return default


def _list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(v) for v in value]


def build_prompt(brief: dict, style: dict | None = None, extra_notes: str = "") -> str:
    style = style or {}
    name = _value(brief, "asset_name", "name", default="Unnamed asset")
    category = _value(brief, "asset_category", "category", default="game asset")
    description = _value(brief, "description", default="")
    intended_use = _value(brief, "intended_use", default="")
    game = _value(brief, "intended_game", default="")
    theme = _value(brief, "theme", default="")
    art_style = _value(brief, "art_style", default=style.get("display_name", ""))
    camera = _value(brief, "camera", default="")
    perspective = _value(brief, "perspective", default="")
    view_direction = _value(brief, "view_direction", default="")
    width = _value(brief, "canvas_width", "width", default="")
    height = _value(brief, "canvas_height", "height", default="")
    background = _value(brief, "background", default="transparent" if brief.get("transparency_required") else "unspecified")
    palette = _value(brief, "colour_palette", "color_palette", default=[])
    outline = _value(brief, "outline_style", default=style.get("line_art", {}).get("outline_width", ""))
    lighting = _value(brief, "lighting_direction", default="")
    shading = _value(brief, "shading_style", default="")
    constraints = _value(brief, "special_constraints", default=[])
    negative = _value(brief, "negative_constraints", default=[])

    style_lines = []
    for key in (
        "description",
        "line_art",
        "palette",
        "shading",
        "lighting",
        "perspective",
        "proportions",
        "detail_density",
        "pixel_grid",
        "anti_aliasing",
        "edge_quality",
        "texture",
    ):
        value = style.get(key)
        if value:
            style_lines.append(f"- {key.replace('_', ' ').title()}: {value}")
    style_mods = _list(style.get("generation_prompt_modifiers"))
    negative_mods = _list(style.get("negative_prompt_modifiers"))
    processing = _list(style.get("processing_rules"))

    lines = [
        "SUBJECT:",
        f"{name} — {description}".strip(" —"),
        f"Asset category: {category}.",
        f"Intended game/use: {game or 'unspecified game'}; {intended_use or 'game asset'}.",
        "",
        "ART DIRECTION:",
        f"Theme: {theme or 'project-appropriate'}.",
        f"Art style: {art_style or 'project style guide'}.",
    ]
    lines.extend(style_lines)
    lines.extend([f"- {m}" for m in style_mods])
    lines.extend(
        [
            "",
            "COMPOSITION:",
            "Single isolated asset, centred with deliberate margins.",
            "Entire silhouette visible; no cropping at the canvas edge.",
            "Readable shape at final game size; avoid detail that disappears when scaled down.",
            "Consistent proportions with the project's existing assets.",
            "",
            "CAMERA:",
            f"Camera: {camera or 'side view'}.",
            f"Perspective: {perspective or 'orthographic/2D game perspective'}.",
            f"Facing/view direction: {view_direction or 'as specified by the animation'}.",
            "",
            "VISUAL CHARACTERISTICS:",
            f"Palette: {palette if palette else 'follow the project palette'}.",
            f"Outline: {outline or 'follow the project outline rule'}.",
            f"Lighting: {lighting or 'consistent single key light'}.",
            f"Shading: {shading or 'follow the project shading model'}.",
            "",
            "BACKGROUND:",
            f"{background}. If transparency is requested, use a clean solid chroma background and do not paint a scene behind the subject.",
            "",
            "GAME ASSET REQUIREMENTS:",
            "- One asset only; no contact sheet, grid, labels, border or UI chrome unless explicitly requested.",
            "- Clean silhouette and separated limbs/parts where the pose requires them.",
            "- Consistent lighting direction and material appearance.",
            "- No unnecessary props, text, logos, watermarks or signatures.",
            "- Appropriate for the specified game perspective and display size.",
        ]
    )
    if width or height:
        lines.append(f"- Intended canvas: {width or '?'} x {height or '?'} px. Generate at a multiple if exact size is unavailable; never distort the aspect ratio.")
    if processing:
        lines.append("- Planned post-processing: " + "; ".join(processing))
    lines.extend(
        [
            "",
            "OUTPUT:",
            f"{width or '?'}x{height or '?'} PNG" if width or height else "PNG with the intended final dimensions.",
            "Preserve clean edges; no fake transparency baked as a checkerboard.",
            "",
            "NEGATIVE CONSTRAINTS:",
        ]
    )
    defaults = [
        "multiple characters",
        "sprite sheet grid unless requested",
        "text, captions, labels, watermark, signature",
        "cropped head, hands, feet or silhouette",
        "busy background",
        "inconsistent lighting",
        "blurry edges",
        "extra limbs or duplicated body parts",
    ]
    for item in defaults + negative_mods + _list(negative):
        if item and item not in lines:
            lines.append(f"- {item}")
    if extra_notes:
        lines.extend(["", "ADDITIONAL PROJECT NOTES:", extra_notes.strip()])
    return "\n".join(lines).strip() + "\n"


def build_prompt_from_files(
    brief_path: str | Path,
    style_path: str | Path | None = None,
    output_path: str | Path | None = None,
    extra_notes: str = "",
) -> str:
    prompt = build_prompt(_load(brief_path), _load(style_path), extra_notes=extra_notes)
    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(prompt, encoding="utf-8")
    return prompt


def negative_prompt(brief: dict, style: dict | None = None) -> str:
    style = style or {}
    parts = [
        "multiple subjects",
        "sprite sheet",
        "text",
        "watermark",
        "signature",
        "cropped",
        "blurry",
        "low contrast",
        "busy background",
        "photorealistic unless requested",
    ]
    parts.extend(_list(style.get("negative_prompt_modifiers")))
    parts.extend(_list(brief.get("negative_constraints")))
    seen = []
    for part in parts:
        if part and part not in seen:
            seen.append(part)
    return ", ".join(seen)
