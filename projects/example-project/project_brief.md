# Mosslight: Project Brief

## Identity

| Field | Value |
|---|---|
| Project | Mosslight |
| Genre | 2D exploration platformer |
| Engine | Godot 4.3 (generic PNGs also produced) |
| Internal resolution | 320x180, integer-scaled |
| Camera | Side-on orthographic, no rotation |
| Target frame rate | 60 fps |
| Art direction | Cozy mossy woodland lit by warm fireflies |

## Visual identity

> A cozy, mossy woodland world lit by warm fireflies.

- Theme: woodland fantasy with quiet, curious exploration.
- Mood: calm, slightly mysterious, never grim.
- Palette: eight anchors, maximum 24 colours per asset. See
  `../../references/styles/palette_mosslight.md`.
- Outline: 1 px at 32 px display, `#1b2a2a` or a hue-shifted dark green.
- Lighting: warm upper-left key, cool ambient fill, amber firefly accents.
- Proportions: characters 32-48 px tall; slimes wider than tall; props grounded.
- Detail budget: readable at 1x; no single-pixel noise unless intentional.

## Prohibited

- Existing copyrighted characters, logos or franchise designs.
- Direct imitation of a named living artist's signature style.
- Baked ground shadows on character sprites (the engine draws them).
- Text, watermarks or signatures inside game art.
- Photorealistic texture in a pixel-art asset.

## Production rules

- **Naming:** `{asset_id}__{animation}__frame_{index:03d}.png`.
- **Source retention:** keep every source and candidate; never overwrite a
  source without a recorded reason.
- **Approval:** technical QA first, then evidence-backed visual review. AI review
  is scoped to internal/demo use; production release needs a human sign-off.
- **Correction limit:** three rounds per asset before escalating.
- **Budget:** 60 credits per asset and 200 per session, if a paid provider is used.

## Scope of this sample

The checked-in sample contains four assets:

| Asset | Category | Purpose |
|---|---|---|
| `moss_slime` | character / creature | Idle 4 frames + walk 6 frames, 64x64, pivot (32, 60) |
| `grass_tile` | environment / ground_tile | 32x32 seamless ground tile |
| `ui_sparkle` | ui / icon | 32x32 transparent pickup/UI icon |
| `sparkle_vfx` | vfx / sparkle | 64x64 six-frame burst effect |

The art is original procedural demo art made by
`../../scripts/build_demo_assets.py` using Pillow. It is **not** AI-generated and
does not demonstrate provider image quality. It demonstrates that the processing,
QA, manifest and export pipeline runs on real pixels.

## Definition of done for the sample

- [x] Every asset has a brief and a frozen style reference.
- [x] Every animated asset has an animation spec before frames exist.
- [x] Frames are aligned to a shared canvas and pivot.
- [x] Technical QA reports exist and pass critical checks.
- [x] Contact sheets and previews exist and were inspected.
- [x] Visual review records reviewer, evidence and approval scope.
- [x] Manifests validate against `schemas/asset_manifest.schema.json`.
- [x] Export folders exist for the documented profiles.
- [x] Known limitations are reported without exaggeration.
