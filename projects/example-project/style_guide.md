# Mosslight Style Guide

The machine-readable source of truth is
[`style_guide.yaml`](style_guide.yaml). This page explains the intent behind it.

## Summary

Mosslight is a cozy 16-bit-inspired woodland style. It uses a restrained
green/amber palette, hard pixel edges, selective 1 px outlines and two-band cel
shading. The smallest gameplay character is 32 px tall, so silhouette and value
structure matter more than interior detail.

## Rules

1. **Pixel grid is real.** No anti-aliasing, no soft brushes, no sub-pixel
   positions. Resize with nearest-neighbour only.
2. **One light direction.** Warm key from the upper-left; cool ambient fill.
   Shadows hue-shift toward blue-green.
3. **Outline is structural.** Use `#1b2a2a` (or a hue-shifted dark green) for the
   silhouette. Interior lines are selective, not a cage around every shape.
4. **Amber is an accent.** Fireflies, interactables and warm highlights only.
   Do not use amber as a generic fill.
5. **No pure black.** Use `#10181c` for the deepest value. The only pure-white
   exception is the 1-2 px core of an emissive sparkle, recorded in the project's
   palette notes.
6. **Detail must survive.** If a detail disappears at the intended display size,
   remove or cluster it.
7. **Transparency is processed, not painted.** Generate on a clean chroma
   background or native alpha, then remove edges locally. Do not paint a fake
   checkerboard.

## Palette

| Hex | Role |
|---|---|
| `#10181c` | Deepest dark, cave depth, outline edge |
| `#1b2a2a` | Default outline, dark wood |
| `#355c4a` | Shadow green |
| `#5f8f5a` | Base green |
| `#a8c66c` | Highlight green |
| `#f2e8c9` | Warm paper, eye white, firefly core |
| `#e7a05a` | Amber accent |
| `#7a4f3a` | Earth brown |

Maximum 24 colours per asset. The eight anchors are not the entire ramp, but any
new ramp colour must sit between anchors and stay hue-consistent.

## Camera and composition

- Side-on orthographic; no vanishing point or perspective rotation.
- Characters are centred with deliberate margins and a bottom-centre pivot.
- Tiles are authored at 32x32 and must wrap cleanly on both axes.
- UI icons are screen-aligned with a 1-2 px optical margin inside the icon box.
- VFX are screen-aligned, centred, and must not obscure gameplay silhouettes.

## Export defaults

| Setting | Value |
|---|---|
| Format | PNG, RGBA |
| Resample | Nearest |
| Integer scale | Yes |
| Sprite sheets | Horizontal, declared cell size, JSON sidecar |
| Godot | Nearest texture filter, SpriteFrames `.tres` |
| Unity | Point filter, Multiple sprite mode, 100 PPU |

## Review checklist

- [ ] Silhouette reads at the intended display size.
- [ ] Palette stays within the anchors plus recorded exceptions.
- [ ] Outline weight matches neighbouring assets.
- [ ] Lighting direction matches the guide.
- [ ] Transparent edges are clean at 1x and 2x.
- [ ] Animation pivot/ground contact is stable.
- [ ] No prohibited content, text or baked shadow.
