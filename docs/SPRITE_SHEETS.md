# Sprite Sheets

A sprite sheet is a delivery format, not a substitute for frame validation. The
layout must be declared and recorded; never infer columns/rows from the image
content and hope.

## Layouts

- **Horizontal:** one row, N columns. Good for simple engine slicing.
- **Vertical:** one column, N rows.
- **Grid:** configurable columns and rows. Good for large sets, but easier to
  mis-slice.
- **Individual frames:** safest for engines that build animations from separate
  textures.

Supported options:

- cell width/height;
- spacing between cells;
- outer margin;
- transparent background;
- per-frame durations;
- sheet sidecar JSON;
- variable frame sizes in individual-frame exports (not in a fixed-grid sheet).

## Cell size vs content size

A sheet cell can be larger than the sprite content. That padding is useful for
pivot consistency and prevents bleed. Keep it consistent across frames.

Do not trim each frame to its own content before packing unless the animation
spec explicitly says to. Tight cropping changes the subject's position within the
canvas and causes jitter.

## Slicing

Declare either columns/rows or cell dimensions (or both):

```powershell
python tools/slice_spritesheet.py sheet.png `
  --columns 4 --rows 2 `
  --cell-width 64 --cell-height 64 `
  --margin 0 --spacing 0 `
  --out-dir frames --metadata frames.json
```

The tool:

- computes the grid and validates that it fits the sheet;
- crops each cell;
- records empty cells instead of silently inventing frames;
- writes a metadata JSON with cell rects;
- refuses to overwrite existing frames unless `--overwrite`.

If the sheet has an alpha channel, inspect the cell edges for bleed from
neighbouring frames. Add spacing if needed.

## Assembly

```powershell
python tools/build_spritesheet.py working/aligned `
  --output spritesheets/moss_slime__walk__sheet.png `
  --metadata spritesheets/moss_slime__walk__sheet.json `
  --layout horizontal
```

The sidecar is authoritative. It contains:

- sheet dimensions;
- grid layout;
- cell size, spacing and margin;
- per-frame x/y/width/height;
- optional durations.

Do not hand-write a sheet sidecar that disagrees with the image. Rebuild it.

## Frame naming

Recommended:

```text
character_name__idle__frame_000.png
character_name__idle__frame_001.png
character_name__walk__frame_000.png
```

Natural sort handles numeric suffixes. Avoid spaces and ambiguous names like
`frame1`, `frame10`, `frame2`; use zero-padded indices.

## Tilesets and autotiles

- Square tiles are easiest; rectangular tiles need explicit cell dimensions.
- Verify opposing edges with `tools/tile_seam_check.py`.
- For autotiles, validate every edge/corner combination, not just the isolated
  tile. Generate an assembled 3x3 or larger preview.
- Isometric tiles need a declared footprint and height; a visually attractive
  tile with the wrong footprint will not connect.
- Animated tiles need frame timing and a loop check, just like character
  animations.

Example:

```powershell
python tools/tile_seam_check.py tiles/grass_32.png `
  --preview qa/grass_wrap.png `
  --assembled qa/grass_assembled_3x3.png `
  --report qa/grass_seam.json
```

A seam warning is not automatic rejection. Inspect the wrap and assembled
preview: some styles intentionally have a strong boundary. What matters is that
the repeated result looks correct in context.

## Packing an atlas

```powershell
python tools/pack_atlas.py frames/ `
  --output atlas/moss_slime.png `
  --metadata atlas/moss_slime.json `
  --max-width 1024 --max-height 1024 --padding 2
```

The packer uses a deterministic shelf algorithm and writes frame rects. It does
not rotate frames. Power-of-two sizing is optional.

## Validation checklist

- [ ] The grid is declared in metadata and matches the image.
- [ ] Cell dimensions are positive and consistent.
- [ ] Every expected frame is present; empty cells are listed.
- [ ] No frame is clipped by a cell boundary.
- [ ] No bleed from adjacent cells.
- [ ] Transparent background where required.
- [ ] Frame order matches the animation spec.
- [ ] Pivot is stored and matches the animation spec.
- [ ] Durations are present when non-uniform timing is used.
- [ ] Contact sheet inspected cell by cell.
- [ ] Animated preview inspected at intended fps.
- [ ] Engine import matches the sidecar (rect origin, pivot convention).

## Common errors

| Error | Cause | Fix |
|---|---|---|
| Frames cut off | wrong cell size or margin | recompute grid; increase cell size/margin |
| Bleed between cells | no spacing/filtering | add spacing; use nearest filtering for pixel art |
| Animation order wrong | filename sorting or row-major assumptions | rename with zero-padded indices; record order |
| Pivot drifts | per-frame trimming | align frames before packing |
| Sheet looks right, engine spins | sidecar uses different rect origin | document top-left origin; match engine import |
| Empty frames appear | sheet includes blank cells | record/skip empty cells; re-check spec |
