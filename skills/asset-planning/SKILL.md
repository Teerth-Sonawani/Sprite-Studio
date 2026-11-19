---
name: asset-planning
description: Turn an underspecified 2D asset request into a validated, testable asset brief with category, canvas, pivot, animation and export constraints.
---

# Asset Planning

## Purpose

Prevent expensive generation from starting before the asset is understood. The
output is a structured brief that every later stage can read.

## Use when

- A request is vague ("a slime", "some grass", "a button").
- A new asset family or project starts.
- An asset needs multiple animations or engine variants.
- Scope, size, pivot or transparency is unclear.

## Inputs

- `projects/<project>/project_brief.md`
- `projects/<project>/style_guide.yaml`
- `config/asset_categories.yaml`
- `config/quality_profiles.yaml`
- `config/animation_presets.yaml`
- `templates/asset_brief.yaml`

## Procedure

1. **Name the asset.** Choose an id in lowercase snake_case, for example
   `character_moss_slime_01`. Do not reuse an id for a different design.
2. **Classify it.** Choose the category and subcategory from
   `config/asset_categories.yaml`. If no category fits, add one; do not
   misclassify. Record its QA profile.
3. **Define the use.** State the game, gameplay role, camera, perspective and
   on-screen size. "Readable at 32px" is a requirement; "looks nice" is not.
4. **Choose the canvas and display size.** Canvas includes padding; display size
   is the in-game size. A 64x64 canvas rendered at 32x32 is valid. Record both.
5. **Set the pivot and contact.** For characters, bottom-centre at the feet. For
   UI, centre. For tiles, top-left. State the ground contact convention.
6. **Decide transparency.** Required for characters, props, UI and VFX. Tiles and
   backgrounds usually opaque. If chroma generation is planned, name the chroma
   colour and forbid it in the art.
7. **List animations.** Use presets as starting points, then override. Record
   frame count, fps, loop type, direction and alignment. For jump/fall, preserve
   authored vertical motion.
8. **List dependencies and references.** Which approved asset defines the style
   or scale? What must be produced first?
9. **Define acceptance criteria.** Technical (size, alpha, padding, palette) and
   visual (silhouette, identity, edges, readability).
10. **Record unknowns.** Make an explicit assumption or ask. Never hide an
    assumption in prose.
11. **Validate.** Check the brief against `schemas/asset_brief.schema.json` and
    the chosen QA profile.

## Output

`projects/<project>/assets/briefs/<asset_id>.yaml` containing at least:

```yaml
asset_id: character_moss_slime_01
asset_name: Moss Slime
asset_category: character
asset_subcategory: creature
intended_game: Mosslight
intended_use: Player-controlled platformer character, 32px tall in game
canvas_width: 64
canvas_height: 64
target_width: 32
target_height: 32
transparency_required: true
pivot: { x: 32, y: 60 }
anchor_point: bottom-center
art_style: pixel_16
animation_required: true
animation_type: idle
frame_count: 4
frame_rate: 6
looping: true
target_engine: godot
export_format: png + sprite sheet + manifest
quality_requirements: [...]
negative_constraints: [...]
```

## Handoff

Send the brief path, not a paraphrase, to `art-direction`, `sprite-generation`
and `quality-assurance`. State which fields are assumptions.

## Quality gate

- [ ] Category exists or was added deliberately.
- [ ] Canvas, display size, pivot and transparency are explicit.
- [ ] Animation timing is explicit or explicitly deferred.
- [ ] Acceptance criteria are measurable.
- [ ] The brief validates against the schema.

## Pitfalls

- Choosing a canvas that cannot hold the silhouette plus padding.
- Forgetting that a 512px render must still read at 32px.
- Treating a preset as mandatory instead of a starting point.
- Mixing perspective or scale with existing assets.
- Planning a sprite sheet before deciding whether the engine wants frames or a
  sheet.
