# Worked Brief: From Vague Request to Validated Spec

This walkthrough uses the example project's moss slime walk cycle. It shows the
decisions that must be recorded before an image is generated or drawn.

## 1. The request

> "Make me a cute moss slime for the platformer. It should walk."

This is not a brief. It does not say size, camera, pivot, animation length,
palette, transparency, engine or acceptance criteria.

## 2. Questions that change the output

| Question | Answer for this project |
|---|---|
| What is the final display size? | 32 px tall; authored at 64x64 for a 2x pixel grid |
| Side-on, 3/4 or top-down? | Side-on orthographic, facing right |
| Is it animated? | Yes: idle 4 frames and walk 6 frames |
| What is the pivot? | Bottom-centre at `(32, 60)` on a 64x64 canvas |
| Is the background transparent? | Yes, with at least 2 px clear padding |
| Which engine? | Godot 4.3; also export generic PNGs |
| What is the palette? | Eight Mosslight anchors, maximum 24 colours |
| What is explicitly forbidden? | Baked shadow, props, text, extra limbs, franchise characters |
| How is it approved? | Technical QA plus evidence-backed visual review; human sign-off separate |

## 3. The brief

The filled brief is
[`projects/example-project/assets/briefs/moss_slime.yaml`](../../projects/example-project/assets/briefs/moss_slime.yaml).
The essential fields are:

```yaml
asset_id: moss_slime
asset_name: Moss Slime
asset_category: character
asset_subcategory: creature
canvas_width: 64
canvas_height: 64
target_width: 32
target_height: 32
transparency_required: true
pivot: {x: 32, y: 60}
anchor_point: bottom-center
animation_required: true
target_engine: godot
```

The `asset_id` matches `[A-Za-z0-9_.-]+`, the pivot is inside the canvas, and the
category exists in `config/asset_categories.yaml`.

## 4. Validate the brief

Before using it, check required fields and types:

```powershell
python -c "import json,yaml,jsonschema; b=yaml.safe_load(open('projects/example-project/assets/briefs/moss_slime.yaml',encoding='utf-8')); s=json.load(open('schemas/asset_brief.schema.json',encoding='utf-8')); jsonschema.validate(b,s); print('brief: PASS')"
```

A schema pass only proves structure. A reviewer still has to confirm that the
brief describes the right asset.

## 5. Build the prompt

```powershell
python tools/build_prompt.py `
  projects/example-project/assets/briefs/moss_slime.yaml `
  --style projects/example-project/style_guide.yaml `
  --output projects/example-project/assets/source/prompts/moss_slime_walk.prompt.txt `
  --extra-notes "Walk cycle only. Six frames. Keep the fern and eyes identical."
```

The generated prompt should repeat the canvas, camera, palette, transparency and
negative constraints. It should not contain credentials, file-system secrets or a
request to imitate a named living artist.

## 6. Write the animation spec

The walk cycle has its own file:
[`projects/example-project/animations/moss_slime_walk.yaml`](../../projects/example-project/animations/moss_slime_walk.yaml).
It records:

- 6 frames at 10 fps, looping;
- per-frame pose and 100 ms duration;
- pivot `(32, 60)` and a 64x64 canvas;
- the transition requirement `frame 5 -> frame 0`;
- the sheet layout used for export.

## 7. Acceptance criteria

An asset is not accepted because the image exists. For this brief:

- [ ] Six non-empty frames, all 64x64, all bottom-aligned to `(32, 60)`.
- [ ] Silhouette still reads when displayed at 32 px.
- [ ] Fern and eyes keep their identity across the cycle.
- [ ] No frame touches the canvas edge; at least 2 px padding.
- [ ] Palette stays within the style guide plus any recorded exception.
- [ ] `tools/validate_animation.py` reports no `FAIL`.
- [ ] Contact sheet and preview were inspected and cited in the review.
- [ ] Manifest hashes match the delivered files.
- [ ] `human_approved` stays `false` unless a human actually signed off.

## 8. Common failure at this stage

The most common bad brief is a wish list with no measurable constraint:

```yaml
# Do not do this
description: "Make it look amazing and professional"
```

Replace it with testable statements:

```yaml
quality_requirements:
  - silhouette readable at 32x32
  - transparent background with no coloured fringe
  - consistent pivot and ground contact
```

## 9. Handoff package

A generation handoff should contain paths, not prose:

```yaml
from: asset_planner
to: sprite_generator
asset_id: moss_slime
brief: projects/example-project/assets/briefs/moss_slime.yaml
style: projects/example-project/style_guide.yaml
animation: projects/example-project/animations/moss_slime_walk.yaml
prompt_file: projects/example-project/assets/source/prompts/moss_slime_walk.prompt.txt
candidates: 3
max_credits: 30
acceptance:
  - one subject, transparent background
  - six-frame walk cycle, pivot (32, 60)
  - readable at 32 px
```

The generator returns candidates with provenance. The pipeline inspects,
processes, validates and reviews them; generation alone is not delivery.
