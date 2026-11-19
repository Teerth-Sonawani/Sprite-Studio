# Mosslight: Worked Art Direction

This is the art-direction example used by `projects/example-project`. It turns a
mood sentence into decisions that a generator, a pixel artist and a reviewer can
all check. The palette itself lives in
[`../styles/palette_mosslight.md`](../styles/palette_mosslight.md).

## Starting point

> A cozy, mossy woodland world lit by warm fireflies.

That sentence is useful for mood and useless for production. The questions below
turn it into constraints.

| Question | Decision | Why it matters |
|---|---|---|
| Camera | Side-on orthographic, no rotation | Tiles, characters and parallax must share one projection |
| Internal resolution | 320x180, integer-scaled | Defines the smallest readable detail |
| Character scale | 32-48 px tall; slimes wider than tall | Prevents object-scale drift between assets |
| Palette | Eight anchors, maximum 24 colours | Keeps a set coherent without forcing a flat look |
| Outline | 1 px (`#1b2a2a` at 32 px display), selective interior lines | Separates silhouettes without a comic-book look |
| Lighting | Warm upper-left key, cool ambient fill | Makes form direction consistent across frames |
| Shading | Two-band cel shading with hard edges | Survives animation and palette quantisation |
| Texture | Sparse 1 px clusters only where they read at 1x | Stops noisy detail that disappears at game size |
| Motion | Calm, weighty, small arcs | Matches the exploration pace and keeps pivots stable |

## Visual pillars

1. **Readable first.** Every asset must be identifiable as a silhouette at its
   final display size. Detail is added only after the shape works.
2. **Moss and warmth.** Cool green structure carries the environment; amber is
   reserved for warmth, interactables and fireflies.
3. **Soft world, hard pixels.** Shapes are rounded, but edges are crisp and
   clusters are deliberate. No anti-aliasing, no blurred gradients.
4. **Quiet contrast.** Backgrounds sit a value step behind characters. Nothing
   in the background competes with gameplay silhouettes.

## Palette roles

| Role | Anchor | Notes |
|---|---|---|
| Deepest dark | `#10181c` | Outline edge, cave depth, text shadow |
| Neutral dark | `#1b2a2a` | Default outline and dark wood |
| Shadow green | `#355c4a` | Slime underside, foliage shadow |
| Base green | `#5f8f5a` | Main moss/slime body, grass base |
| Highlight green | `#a8c66c` | Sunlit moss and leaf highlights |
| Warm paper | `#f2e8c9` | Eye white, UI text, firefly core |
| Amber | `#e7a05a` | Fireflies, warm wood, interaction |
| Earth | `#7a4f3a` | Trunks, soil, leather |

Amber is an accent, not a fill. The sparkle assets use a pure-white core as a
recorded exception to the "no pure white" rule; that exception is limited to the
brightest 1-2 px of an emissive effect.

## Shape language

- **Characters:** rounded primary mass, one dominant direction of lean, feet or
  base clearly grounded. Slimes are wider than tall and squash vertically.
- **Environment:** chunky masses, readable negative space, no thin 1 px twigs
  that vanish at 1x. Tiles use periodic structure so edges connect.
- **UI:** geometric, symmetrical where possible, with a 1-2 px optical margin
  inside the icon box. Avoid interior detail below 2 px.
- **VFX:** radial or arc-based motion, bright core, amber falloff, no full-screen
  bloom. The effect must not hide the player or the hitbox.

## Lighting and shading rules

- Light comes from the upper-left at roughly 45 degrees.
- Use one hard highlight cluster and one or two hard shadow clusters.
- Hue-shift shadows toward blue-green, not toward grey.
- Do not add a baked ground shadow to a character sprite; the engine draws it.
- Fireflies are small warm accents with a cream core, not large light sources.

## Do / do not

| Do | Do not |
|---|---|
| Test the silhouette at 32 px before adding detail | Judge the asset only at 4x zoom |
| Reuse the same pivot for every frame | Let the feet drift between frames |
| Keep the palette anchors stable across a set | Introduce neon green or pure black |
| Keep the fern cluster inside the canvas | Crop a leaf or horn at the edge |
| Record palette exceptions | Silently break the style guide |

## Acceptance checklist

- [ ] Silhouette reads at 32 px (character), 24 px (UI) or 1x (tile).
- [ ] Transparent assets have no coloured fringe and at least 2 px of padding.
- [ ] Palette stays within the anchors plus recorded exceptions.
- [ ] Outline weight is consistent with other assets in the set.
- [ ] Lighting direction matches the style guide.
- [ ] Animation base/pivot is stable, except where motion is intentional.
- [ ] The reviewer inspected a contact sheet, a preview at intended size and a
      1x view, not only a zoomed image.

## How this becomes a style guide

The production values are copied into
[`projects/example-project/style_guide.yaml`](../../projects/example-project/style_guide.yaml)
and frozen there. The Markdown version explains intent; the YAML is what the
prompt builder and reviewers read. If the two disagree, fix the conflict before
producing more assets.
