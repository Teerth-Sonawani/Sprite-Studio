# Mosslight Example Project

This project is a complete, reproducible walkthrough of the 2D Sprite Studio
pipeline. It plans four assets, builds original demo art, processes and aligns
frames, validates them, records an evidence-backed review, writes manifests and
exports engine packages.

> **Provenance:** the checked-in art is original procedural Pillow art drawn by
> `scripts/build_demo_assets.py`. It is **not AI-generated**. It proves that the
> pipeline works on real pixels; it is not a showcase of any provider's image
> quality. Every manifest records `provider: scripted_pillow` and
> `mode: procedural_demo`.

## Rebuild everything

From the workspace root:

```powershell
python scripts/build_demo_assets.py --stage all
```

Stages are independently runnable:

| Stage | What it does |
|---|---|
| `assets` | Rebuilds sources, working frames, approved frames, sheets, previews and technical QA. Deletes only generated folders/reports it owns. |
| `reviews` | Applies `qa/review_decisions.json` to the technical reports and writes `<asset>_review.json`. |
| `exports` | Builds manifests, verifies every file hash, and writes generic/Godot/Unity exports. |
| `all` | Runs `assets` → `reviews` → `exports`. |

The build is deterministic for the same Pillow version. Re-run it after editing
the procedural drawing functions, briefs, style guide or animation specs.

## Asset inventory

| Asset | Category | Output | QA status |
|---|---|---|---|
| `moss_slime` | character / creature | Idle 4 frames + walk 6 frames, 64×64, pivot (32, 60), two sheets | `APPROVED` (AI, demo scope) |
| `grass_tile` | environment / ground tile | 32×32 seamless tile, 3×3 assembly and 2×2 wrap previews | `APPROVED` (AI, demo scope) |
| `ui_sparkle` | UI / icon | 32×32 transparent star icon | `APPROVED` (AI, demo scope) |
| `sparkle_vfx` | VFX / sparkle | 64×64 six-frame one-shot burst, sheet and previews | `APPROVED` (AI, demo scope) |

`human_approved` is `false` for every asset. An AI review is intentionally scoped
to `demo_or_internal`; production release requires a human sign-off.

## Where things live

```text
projects/example-project/
├── project_brief.md                 Project identity, rules and scope
├── style_guide.md / style_guide.yaml Frozen Mosslight style
├── animations/                      Idle, walk and VFX timing specs
├── assets/
│   ├── briefs/                      One structured brief per asset
│   ├── source/                      Immutable procedural sources and prompts
│   ├── working/                     Pre-alignment processed frames
│   └── approved/                    Final frames, sheets and previews
├── qa/
│   ├── review_decisions.json        Human-authored review inputs
│   ├── *_processing.json            Background/alpha processing evidence
│   ├── *_technical.json             Deterministic technical reports
│   ├── *_animation.json             Animation checks and metrics
│   └── *_review.json                Applied visual-review records
├── manifests/                       Portable manifests and build summary
└── exports/
    ├── generic/                     Per-asset PNG packages + animations.json
    ├── godot/                       SpriteFrames .tres + sheet textures
    ├── unity/                       Sheet PNGs, slice JSON and .meta files
    └── previews/                    Convenience GIF copies
```

## Read the evidence in this order

1. `qa/moss_slime_technical.json` — technical status and per-frame checks.
2. `qa/moss_slime_idle_animation.json` and `qa/moss_slime_walk_animation.json`.
3. `assets/approved/moss_slime/previews/moss_slime__idle__contact.png` and the
   walk contact sheet, then the GIF/WebP previews.
4. `qa/review_decisions.json` — the authored scores, notes and evidence paths.
5. `qa/moss_slime_review.json` — the applied approval and its scope.
6. `manifests/moss_slime.manifest.json` — file hashes, animation bindings and
   provenance.
7. `exports/godot/moss_slime.tres` or `exports/unity/*.slices.json`.

## Commands used by the build

```powershell
# Inspect a frame
python tools/inspect_image.py projects/example-project/assets/approved/moss_slime/frames/idle/moss_slime__idle__frame_000.png --palette

# Validate one frame
python tools/validate_sprite.py projects/example-project/assets/approved/moss_slime/frames/idle/moss_slime__idle__frame_000.png `
  --width 64 --height 64 --transparency --padding 2 --pivot-x 32 --pivot-y 60 `
  --report projects/example-project/qa/frame_technical.json

# Validate an animation
python tools/validate_animation.py projects/example-project/assets/approved/moss_slime/frames/idle `
  --expected-count 4 --pivot-x 32 --pivot-y 60 --frames-per-second 6 `
  --report projects/example-project/qa/idle_animation.json

# Apply reviews and export
python scripts/build_demo_assets.py --stage reviews
python scripts/build_demo_assets.py --stage exports

# Verify the whole suite
python -m pytest -q
```

## QA notes

- Technical checks can only reach `TECHNICAL_PASS`; they never grant `APPROVED`.
- `sparkle_vfx` reports a `scale_variation` warning (0.828 vs the default 0.80
  limit). This is intentional: a burst expands and contracts. The review records
  why the warning is acceptable rather than silently raising the threshold.
- The grass tile passes both seam axes (x ratio 0.444, y ratio 0.821) and was
  inspected in the 3×3 assembled and 2×2 wrap previews.
- All four assets passed deterministic technical checks. The scans, palettes,
  contact sheets and animation metrics live in `qa/`.

## Export notes and limitations

- Manifest paths are relative to the manifest folder; `asset_root` is a fallback.
  The build verifies every manifest hash after export.
- The Godot `.tres` is a real `SpriteFrames` resource using `AtlasTexture`
  regions. The Unity `.meta` and `.slices.json` are import aids; Unity does not
  consume the sidecar automatically. Neither project was opened in the engine.
- Native Aseprite/LibreSprite project writing is not implemented.
- No charged PerchanceAI generation was run for this project. See
  `docs/PERCHANCE_INTEGRATION.md` for the verified API status.
- The demo art is procedural and intentionally simple. Replace it with generated
  or hand-drawn candidates when evaluating provider quality.
