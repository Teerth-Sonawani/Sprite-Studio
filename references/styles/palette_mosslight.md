# Mosslight Palette

The example project's palette. It is a project decision, not a universal style.

| Hex | Role | Use |
|---|---|---|
| `#10181c` | deepest outline / night | Silhouette edge, cave depth, text shadow |
| `#1b2a2a` | outline / dark neutral | Default 1px outline, dark wood |
| `#355c4a` | shadow green | Slime underside, foliage shadow, wall recess |
| `#5f8f5a` | base green | Main moss/slime body, grass base |
| `#a8c66c` | highlight green | Sunlit moss, leaf highlight |
| `#f2e8c9` | warm paper / eye white | Eye highlight, UI text, firefly core |
| `#e7a05a` | amber accent | Fireflies, warm wood, interactive highlight |
| `#7a4f3a` | earth brown | Trunks, soil, leather, secondary shadow |

## Rules

- Maximum 24 colours for a `pixel_16` asset; the eight swatches above are the
  anchors, not the entire ramp.
- Outline uses `#1b2a2a` or a hue-shifted dark green, not pure black.
- Hue-shift shadows toward blue-green, not toward grey.
- Keep amber for warmth and interaction; do not use it as a generic fill.
- Do not introduce neon green, pure white or pure black.
- A palette exception must be recorded in the project changelog and reviewed.

## Contrast checks

- `#5f8f5a` on `#10181c`: strong silhouette separation.
- `#a8c66c` on `#5f8f5a`: highlight separation; use clusters, not single pixels.
- `#f2e8c9` on `#10181c`: high contrast for eyes/UI.
- `#e7a05a` on `#355c4a`: warm accent; check at 32px.

## Application by asset

| Asset | Dominant | Shadow | Highlight | Accent |
|---|---|---|---|---|
| Moss slime | `#5f8f5a` | `#355c4a` | `#a8c66c` | `#f2e8c9` eyes, `#e7a05a` fern tip |
| Grass tile | `#5f8f5a` | `#355c4a` | `#a8c66c` | `#f2e8c9` flower |
| Sparkle icon | `#f2e8c9` | `#e7a05a` | `#ffffff` core (exception) | `#a8c66c` rim |
| Sparkle VFX | `#f2e8c9` | `#e7a05a` | `#ffffff` core | `#a8c66c` secondary |
