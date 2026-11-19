---
name: 2d-sprite-studio
description: Plan, generate, process, animate, validate and export 2D game sprites in this workspace. Use for any sprite, character, creature, tile, environment, UI icon, VFX, animation, sprite-sheet, atlas, QA, manifest or engine-export task.
---

# 2D Sprite Studio

This is the entry point. It routes work to the eleven focused skills and enforces
the workspace's quality gates.

## When to use this skill

Use it when the user asks for any of the following:

- a 2D sprite, character, creature, prop, tile, background, UI icon or VFX;
- an animation, frame sequence, sprite sheet, atlas or animation preview;
- background removal, transparency cleanup, resizing, alignment or palette work;
- a style guide, asset brief, character sheet or art-direction decision;
- sprite QA, manifest generation, provenance or engine export;
- Perchance generation (manual, developer API, or the documented tutorial mode).

## Start every task here

1. Read `AGENTS.md` and `docs/WORKFLOW.md`.
2. Identify the project. If none exists, create one from
   `templates/project_brief.yaml` and a style guide from
   `templates/style_guide.yaml`.
3. Read the project brief and frozen style guide.
4. Create or update an asset brief from `templates/asset_brief.yaml`.
5. Route to the narrowest skills below. Load only what the task needs.
6. Keep a structured handoff between stages.

## Skill router

| If the task is... | Load |
|---|---|
| Scope, category, dependencies, acceptance criteria | `skills/asset-planning/SKILL.md` |
| Style, palette, references, visual consistency | `skills/art-direction/SKILL.md` |
| Character or creature design, expressions, variants | `skills/character-design/SKILL.md` |
| Tiles, terrain, props, backgrounds, parallax | `skills/environment-art/SKILL.md` |
| Pixel grid, palette limits, outlines, dithering | `skills/pixel-art/SKILL.md` |
| Provider choice, prompt, cost, provenance | `skills/sprite-generation/SKILL.md` |
| Background removal, alpha cleanup, resize, crop | `skills/image-processing/SKILL.md` |
| Frame alignment, timing, loops, previews | `skills/animation/SKILL.md` |
| Sheets, grids, slicing, atlases, JSON sidecars | `skills/sprite-sheet-production/SKILL.md` |
| Technical checks, visual review, defect reports | `skills/quality-assurance/SKILL.md` |
| Godot, Unity, generic or Aseprite export | `skills/game-engine-export/SKILL.md` |

## Mandatory pipeline

```text
plan -> reference -> generate -> process -> animate -> validate -> correct -> export
```

Do not collapse the pipeline into "generate an image". If a step is genuinely
not applicable, say why and record it in the asset brief or manifest.

## Hard gates

- A candidate is not game-ready because a generator returned it.
- `tools/validate_sprite.py` can only reach `TECHNICAL_PASS`. It never approves.
- `APPROVED` requires a visual review with evidence paths.
- `human_approved` is separate from AI review and defaults to `false`.
- Chargeable generation requires a prior estimate, a credit limit and `--confirm`.
- Unknown model keys, invented endpoints and fake capabilities are forbidden.
- Perchance Mode A is unsupported. The documented endpoint returned HTTP 404 on
  2026-11-12; do not claim it works.
- Aseprite native project writing is not implemented.

## Output contract

Every delivered asset should have:

```text
assets/approved/<asset_id>/
  frames/                 final PNG frames
  sheets/                 sheet PNGs + JSON sidecars
  previews/               GIF/APNG/WebP/preview at intended size
qa/<asset_id>_technical.json
qa/<asset_id>_review.json
manifests/<asset_id>.manifest.json
exports/<profile>/...
```

Plus a short delivery note: files, dimensions, pivot, animations, QA status,
approval scope, known limitations and next action.

## Tool map

Use the dedicated tools rather than ad-hoc scripts:

- `tools/inspect_image.py`
- `tools/validate_sprite.py`
- `tools/remove_background.py`
- `tools/clean_transparency.py`
- `tools/resize_sprite.py`
- `tools/align_frames.py`
- `tools/slice_spritesheet.py`
- `tools/build_spritesheet.py`
- `tools/make_contact_sheet.py`
- `tools/preview_animation.py`
- `tools/validate_animation.py`
- `tools/palette_check.py`
- `tools/tile_seam_check.py`
- `tools/pack_atlas.py`
- `tools/build_prompt.py`
- `tools/generate_asset.py`
- `tools/import_generated.py`
- `tools/generate_manifest.py`
- `tools/qa_review.py`
- `tools/export_asset.py`

Run `--help` on any tool for exact arguments.

## Reporting rules

- Say "candidate" until it passes the gates.
- Say "TECHNICAL_PASS" for automated checks only.
- Say "APPROVED (demo/internal, human_approved: false)" for AI-reviewed work.
- Never say "perfect", "production-ready" or "human-approved" without evidence.
- Report what is unverified, not just what is present.
