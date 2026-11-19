---
name: art-direction
description: Freeze a project's visual style, palette, lighting, outline and reference board so every asset in a family is consistent and reviewable.
---

# Art Direction

## Purpose

Make style a project decision, not a per-asset mood. The output is a frozen style
guide plus a reference board that later stages can compare against.

## Use when

- Starting a project or a new asset family.
- Assets look inconsistent in scale, palette, lighting or edge quality.
- A provider's output drifts between generations.
- A reviewer needs objective criteria for "on-style".

## Inputs

- `projects/<project>/project_brief.md`
- `config/art_styles.yaml`
- `references/styles/`
- Any approved asset that defines the look
- `templates/style_guide.yaml`

## Procedure

1. **Pick a style family.** Start from a `style_id` in
   `config/art_styles.yaml` (for example `pixel_16`, `vector_flat`,
   `painted_fantasy`). Copy it into the project guide; do not edit the shared
   registry to make a project-only choice.
2. **Write the one-line identity.** Theme, mood, time of day, colour temperature
   and what the player should feel. Keep it short enough to quote in prompts.
3. **Freeze the palette.** Record hex swatches with roles: outline, shadow, base,
   highlight, accent, UI text. State the maximum colour count. For pixel art,
   require clustering and forbid anti-aliasing.
4. **Define line and edge behaviour.** Outline width, colour (often a dark hue,
   not pure black), interior lines, anti-aliasing policy and edge quality.
5. **Define lighting.** Key direction, ambient fill, contrast and whether shadows
   are baked into sprites. Do not bake a drop shadow if the engine draws one.
6. **Define perspective and scale.** Side-on orthographic, 3/4, isometric or
   top-down. State character heights, tile size and prop scale.
7. **Set detail density.** What survives at final game size? For pixel art, ban
   single-pixel noise unless it is intentional and reviewed.
8. **Build a reference board.** Approved idle, tile family, icon grid, palette
   strip and one "off-style" example with reasons. Store paths, not vibes.
9. **Write prompt modifiers.** Add positive and negative phrases that encode the
   guide. Keep them descriptive and original; do not name a living artist or a
   protected character.
10. **Freeze and version it.** Record the date and version. Changes after assets
    exist require a changelog entry and a re-review plan.

## Output

- `projects/<project>/style_guide.md` — human-readable guide.
- `projects/<project>/style_guide.yaml` — machine-readable guide used by prompts
  and manifests.
- `projects/<project>/references/` — palette strip, approved reference board and
  annotated comparisons.

## Handoff

Give `sprite-generation` the style guide path and the exact prompt modifiers.
Give `quality-assurance` the visual checklist and reference board.

## Quality gate

- [ ] Style family and style id are recorded.
- [ ] Palette has roles, hex values and a maximum count.
- [ ] Outline, lighting, perspective and scale rules are explicit.
- [ ] At least one approved reference exists or is scheduled.
- [ ] Prompt modifiers and negative constraints are present.
- [ ] No protected character, logo or named-artist imitation is requested.

## Pitfalls

- A style guide that only contains adjectives ("cozy", "vibrant") is not usable.
- Mixing pixel sizes or outline widths across a family.
- Changing the palette mid-family without re-reviewing earlier assets.
- Asking a generator for "in the style of [living artist]".
- Baked shadows that fight the engine's lighting.
