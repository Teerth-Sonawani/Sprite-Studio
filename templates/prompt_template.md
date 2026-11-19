# Prompt Template

Use this as a checklist, not a fixed incantation. Adapt it to the provider and
the asset. The prompt is not evidence that the output is usable: verify actual
dimensions, transparency, pose and frame consistency after generation.

```text
SUBJECT:
[Exact asset description, one asset only]

ART DIRECTION:
[Project style guide: palette, outlines, shading, lighting, proportions]

COMPOSITION:
[Position, orientation, framing, negative space, silhouette]
[For animation frames: exact pose and phase; reference the approved base design]

CAMERA:
[View angle, perspective, facing direction]

VISUAL CHARACTERISTICS:
[Palette, materials, line weight, detail budget, edge quality]

BACKGROUND:
[Transparent / solid chroma / explicitly described scene]
[State that a checkerboard must not be painted into the image]

GAME ASSET REQUIREMENTS:
- Entire asset visible.
- No unwanted cropping.
- Clean silhouette.
- Consistent lighting.
- No unnecessary objects.
- Appropriate for the specified game perspective.
- Readable at the intended in-game size.

OUTPUT:
[Requested dimensions and format]
[If exact dimensions are unsupported: generate at a larger multiple and state it]

NEGATIVE CONSTRAINTS:
[Asset-specific unwanted features]
[No text, watermark, signature, logos, extra limbs, duplicated subjects]
```

## Frame/prompt discipline

- For frame *n*, state the frame index, total count, pose phase and movement
  direction. Do not ask for "a walk cycle sheet" unless the provider genuinely
  supports reliable grids.
- When using reference conditioning, state which features must remain fixed
  (silhouette, palette, costume, eye spacing) and which may change (limb pose).
- Preserve source files and the exact prompt. A repaired asset needs a record of
  what was changed.
- If a defect is local (a stray pixel, one bad alpha island), correct the image
  rather than regenerating the whole asset.
