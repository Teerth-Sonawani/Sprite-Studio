---
name: environment-art
description: Design 2D tiles, terrain, props, backgrounds and parallax layers with correct scale, perspective, seams and gameplay readability.
---

# Environment Art

## Purpose

Produce environment assets that assemble correctly, preserve the project's
perspective and scale, and stay readable behind characters and effects.

## Use when

- Creating ground tiles, walls, platforms, props, foliage, water or backgrounds.
- Building a tileset, autotile or parallax layer.
- An environment asset must tile seamlessly or connect to neighbours.
- A background must support foreground gameplay without stealing contrast.

## Inputs

- Project brief, style guide and asset brief
- Target tile size and camera resolution
- Neighbouring tiles or the approved tile family
- `config/quality_profiles.yaml` (`tile`, `environment`, `background`)
- `templates/asset_brief.yaml`

## Procedure

1. **Lock the grid.** Record tile width/height, character height, camera scale
   and the projection (side-on, 3/4, isometric, top-down). Do not mix grids.
2. **Separate gameplay from decoration.** Decide which pixels are collision,
   which are overlay and which are pure background. A beautiful tile that hides
   the platform edge is a failure.
3. **Design the base tile first.** Keep the centre calm and push detail toward
   edges only when it helps assembly. Avoid high-frequency noise that creates
   visible tiling.
4. **Make seams intentional.** For seamless tiles, compare the wrap transition
   with the interior gradient. Run `tools/tile_seam_check.py` and inspect the
   assembled preview, not just the single tile.
5. **Design edge and corner variants.** For platforms and walls, plan top, left,
   right, inner and outer corners. Record adjacency rules.
6. **Mind value structure.** Backgrounds need lower contrast and cooler values
   than gameplay elements. Foreground props need a readable silhouette against
   the busiest expected background.
7. **Plan parallax layers.** Separate sky, far, mid, near and foreground. Record
   scroll factors and overlap. Avoid detail that reveals the repeat.
8. **Scale-check against characters.** Put a character silhouette next to the
   prop or tile. Doors, crates and foliage must feel proportionate.
9. **Check colour and lighting.** Match the project key light and palette. Do not
   introduce a new light direction for one prop.
10. **Validate.**
    - `tools/tile_seam_check.py` for repeating tiles.
    - `tools/inspect_image.py` for dimensions and alpha.
    - `tools/validate_sprite.py` with the tile/environment profile.
    - An assembled 3x3 or 2x2 preview.

## Output

- Tile or prop PNGs under `assets/approved/<asset_id>/`
- Tileset/family preview and seam report under `qa/`
- Placement notes: tile size, pivot, adjacency, collision notes and parallax
  factor.

## Handoff

Send tile size, adjacency rules and seam report to `sprite-sheet-production` and
`game-engine-export`. Send the assembled preview to `quality-assurance`.

## Quality gate

- [ ] Grid, perspective and scale match the project.
- [ ] Tiles wrap cleanly or have documented edge variants.
- [ ] Gameplay edges remain readable.
- [ ] Background contrast does not fight foreground assets.
- [ ] Props read at gameplay size.
- [ ] Lighting and palette match the style guide.

## Pitfalls

- Judging a tile only at 1x on a checkerboard, never assembled.
- Adding single-pixel noise that turns into a visible grid.
- Mixing isometric footprints with side-on characters.
- Using the same contrast for background and interactive props.
- Drawing a prop at a different scale than the character.
