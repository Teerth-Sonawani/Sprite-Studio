# Style Selector

Use this matrix to narrow the style family before writing a project style guide.
It is guidance, not a rule. The project brief and target display size win.

| Need | Good starting styles | Avoid |
|---|---|---|
| 16-32px platformer character | `pixel_16`, `pixel_32` | `painted_fantasy`, `watercolour` |
| Readable HUD icon at 24-32px | `ui_icon`, `pixel_16`, `vector_flat` | High-detail painted art |
| Soft magic/VFX at 64-128px | `vfx_sprite`, `painted_fantasy` (for key art) | `one_bit` unless silhouettes are the point |
| Cozy woodland world | `pixel_16`, `hand_drawn_ink`, `paper_cut` | Photorealistic texture |
| Isometric management/tactics | `isometric`, `pixel_32`, `lowpoly_2d` | Side-on perspective mixed in |
| Clean mobile UI | `vector_flat`, `ui_icon` | Pixel grid unless the whole UI is pixel |
| Dramatic key art / store art | `painted_fantasy`, `cel_shaded_anime` | 16px-detail constraints |
| Monochrome puzzle/game jam | `one_bit` | Reliance on colour cues |

## Selection questions

1. **What is the smallest display size?** If detail disappears below 32px, use a
   lower-detail style or simplify the design.
2. **Is the camera side-on, 3/4, isometric or top-down?** Lock it before choosing
   shading.
3. **Does the project need animation?** Styles with hard edges and clustered
   shading are easier to keep consistent across frames.
4. **Will the art be generated or hand-authored?** Generated art often drifts;
   choose a style with strong, simple invariants and plan reference conditioning.
5. **What does the engine filter look like?** Pixel art needs nearest filtering
   and integer scaling.
6. **How much colour variety is needed?** `one_bit` and `pixel_16` are constraints,
   not just aesthetics.

## Style-to-processing map

| Style | Resample | Background removal | Palette |
|---|---|---|---|
| `pixel_16`, `pixel_32`, `one_bit` | nearest | edge-aware, hard alpha | quantise to limit |
| `ui_icon` | nearest or lanczos | edge-aware or native alpha | per-icon limit |
| `vector_flat` | lanczos | preserve smooth edges | flat fills |
| `hand_drawn_ink`, `watercolour` | lanczos | edge-aware, preserve semi-transparent wash | avoid global key |
| `painted_fantasy` | lanczos | edge-aware, inspect fringe | open |
| `isometric` | nearest (pixel) or lanczos (painted) | grid-aware crop | style-dependent |
| `vfx_sprite` | nearest for pixel FX, lanczos for painted | preserve alpha falloff | effect-limited |

## Red flags

- The style guide says "pixel art" but the reference has anti-aliased edges.
- The palette limit is lower than the shading model needs.
- The project mixes isometric tiles with side-on characters.
- The style depends on a named artist's signature rather than describable traits.
- The smallest UI size is 16px but the icon has interior detail below 2px.
