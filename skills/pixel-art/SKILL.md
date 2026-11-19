---
name: pixel-art
description: Enforce pixel-grid, palette, outline, dithering and scaling rules for pixel-art sprites, tiles and animations.
---

# Pixel Art

## Purpose

Keep pixel art genuinely pixel-aligned instead of a smooth illustration shrunk
down. Apply the project's grid, palette and edge rules at every stage.

## Use when

- The style id is `pixel_16`, `pixel_32`, `one_bit`, pixel UI or pixel VFX.
- A generated or painted image must become pixel art.
- Frames or tiles show anti-aliasing, colour drift, uneven pixel sizes or blur.
- Scaling or exporting to an engine.

## Inputs

- Project style guide with pixel rules
- `config/studio.yaml` `pixel_art` section
- Asset brief with canvas and display size
- Approved reference sprite or tile

## Rules

1. **One logical pixel = one image pixel at authored resolution.** Do not author
   at 4x and call every fourth pixel a pixel unless the project explicitly uses a
   high-resolution pixel style.
2. **Nearest-neighbour only for scaling.** Use
   `tools/resize_sprite.py --scale N` or `--method nearest`. Never use Lanczos or
   bicubic on pixel art.
3. **Integer scale factors preferred.** 2x, 3x, 4x. Fractional scaling creates
   uneven pixel sizes.
4. **Palette is intentional.** Stay within the style guide's limit. Record the
   swatches. Use hue-shifted ramps, not black-to-white ramps.
5. **No accidental anti-aliasing.** Hard edges. If semi-transparent edge pixels
   are used deliberately (for example soft VFX), record it as an exception.
6. **Cluster detail.** Avoid single-pixel noise unless it is a deliberate texture
   that survives at 1x.
7. **Selective outline.** Use a hue-shifted dark tone, not pure black, unless the
   style explicitly calls for pure black. Interior lines only where form needs
   separation.
8. **Consistent light.** Pick a key direction and keep it across the family.
9. **Silhouette first.** Test the sprite in solid colour at final size before
   adding interior detail.
10. **Pixel-perfect placement.** Keep feet, pivots and tile boundaries on integer
    pixel coordinates. Do not resample frames independently.

## Procedure

1. Author or convert at the target resolution.
2. Quantise the palette deliberately:
   `tools/palette_check.py IMAGE --limit N --quantize OUT`.
3. Inspect the palette and edge quality.
4. Remove anti-aliasing or fringe with `tools/clean_transparency.py` only when it
   is genuinely unwanted; do not destroy intentional soft VFX.
5. Resize with nearest-neighbour if needed.
6. Validate dimensions, pivot, palette and transparency.
7. Preview at 1x and 2x on light, dark and busy backgrounds.
8. For animation, check that the pixel grid does not jitter between frames.

## Output

- Pixel-aligned PNG frames and sheets
- Palette report
- 1x/2x previews
- Notes on any deliberate anti-aliasing or palette exception

## Handoff

Send the palette report and pixel-grid decision to `image-processing`,
`sprite-sheet-production` and `game-engine-export` (nearest filtering).

## Quality gate

- [ ] No unintended anti-aliasing.
- [ ] Palette within the declared limit.
- [ ] Integer scaling only.
- [ ] Consistent pixel size across frames.
- [ ] Silhouette reads at 1x.
- [ ] Outline and light direction match the guide.

## Pitfalls

- Generating at 1024px and downscaling with Lanczos.
- Using a "pixel art" prompt but accepting smooth edges.
- Adding a 1px outline after scaling, producing an uneven border.
- Allowing palette drift between animation frames.
- Treating a soft VFX exception as a licence to blur all pixel art.
