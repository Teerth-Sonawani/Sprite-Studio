---
name: sprite-sheet-production
description: Build, slice, label and validate sprite sheets and texture atlases with authoritative JSON sidecars for engines and animation pipelines.
---

# Sprite Sheet Production

## Purpose

Turn a frame sequence into a deterministic sheet or atlas without losing frame
identity, timing, pivot or cell geometry.

## Use when

- An engine or tool expects a single texture instead of frame files.
- A sheet must be sliced back into frames.
- Frames need padding/spacing to avoid bleeding.
- A texture atlas is needed for props or UI.
- Sheet metadata must be authoritative and reproducible.

## Inputs

- Aligned frames with consistent canvas and pivot
- Animation spec (frame order, durations, loop)
- `config/studio.yaml` naming rules
- `config/export_profiles.yaml`
- Target engine's cell/spacing/filtering expectations

## Procedure

### Build a sheet

```powershell
python tools/build_spritesheet.py ALIGNED_FRAMES `
  --output sheets/moss_slime__idle__sheet.png `
  --metadata sheets/moss_slime__idle__sheet.json `
  --layout horizontal --spacing 0 --margin 0 `
  --durations 166,166,166,166 --overwrite
```

- Frames are written in natural filename order.
- `build_sheet` centres each frame inside its cell and records the actual frame
  rect and the full cell rect. Do not assume the frame fills the cell.
- Use `--layout grid --columns N --rows M` when the engine wants a grid.
- Add spacing when filtering or compression could bleed between frames.
- Never rely on the image dimensions to infer the grid. The sidecar is
  authoritative.

### Slice a sheet

```powershell
python tools/slice_spritesheet.py sheets/moss_slime__idle__sheet.png `
  --columns 4 --rows 1 --cell-width 64 --cell-height 64 `
  --out-dir frames/sliced --prefix moss_slime `
  --metadata qa/sliced_layout.json --overwrite
```

- Declare the grid. The tool does not guess it from content.
- Empty cells are recorded. `--keep-empty` writes transparent frame files instead
  of skipping them.
- Verify the sliced frames match the expected animation count and order.

### Build an atlas

```powershell
python tools/pack_atlas.py ALIGNED_FRAMES props/icon.png `
  --output atlas/game_atlas.png --metadata atlas/game_atlas.json `
  --max-width 1024 --max-height 1024 --padding 2 --pot --sort height --overwrite
```

The shelf packer records each item's rect and optional pivot. Atlas order is a
packing decision, not an animation order; keep animation frame order in the
animation spec or sheet sidecar.

### Validate

- Compare frame count in the sidecar with the animation spec.
- Compare sheet dimensions with `columns * cell_width + spacing + margin`.
- Check that every cell is unique where expected.
- Inspect the sheet at 1x; look for bleed, crop, duplicated frames and labels.
- For atlas, verify no overlapping rects and that every source is represented.
- For pixel art, confirm no filtering or scaling was applied.

## Naming

```text
<asset_id>__<animation>__sheet.png
<asset_id>__<animation>__sheet.json
<asset_id>__atlas.png
<asset_id>__atlas.json
```

## Output

- Sheet/atlas PNG
- JSON sidecar with layout, frame rects, cell rects, durations and source hashes
  where applicable
- Sliced frames (when round-tripping)
- Validation notes

## Handoff

Send the sheet, sidecar, frame count and durations to `game-engine-export` and
`quality-assurance`. Never send only the PNG.

## Quality gate

- [ ] Grid/cell dimensions are declared and documented.
- [ ] Sidecar frame rects and durations match the animation spec.
- [ ] No accidental crop or bleed between cells.
- [ ] Empty cells are recorded.
- [ ] Slicing round-trips to the expected frame count.
- [ ] Atlas rects do not overlap.

## Pitfalls

- Assuming a 4x4 grid because the sheet looks square.
- Cropping at cell boundaries when frames have different bboxes.
- Leaving no padding and then enabling bilinear filtering.
- Shipping a sheet without its sidecar.
- Reordering frames to make packing easier, then losing animation timing.
