---
name: image-processing
description: Inspect, clean, matte, crop, resize and align 2D sprites so raw generator output becomes a game-ready RGBA asset with auditable reports.
---

# Image Processing

## Purpose

Turn a source image into a clean, correctly sized RGBA asset without destroying
intentional detail. Every destructive step should have a report.

## Use when

- A generated or painted image needs a transparent background.
- Alpha fringes, islands or holes need cleanup.
- A sprite needs cropping, padding, resizing or canvas alignment.
- A source must be checked before animation.

## Inputs

- Source image and its provenance sidecar
- Asset brief (canvas, display size, pivot, transparency)
- Style guide (resampling, edge and palette rules)
- `config/quality_profiles.yaml`

## Procedure

### 1. Inspect before editing

```powershell
python tools/inspect_image.py SOURCE.png --palette --report qa/source_inspect.json
```

Check dimensions, mode, alpha coverage, bounding box, palette and hash. Never
assume a generated file is RGBA or transparent.

### 2. Remove the backdrop

```powershell
python tools/remove_background.py SOURCE.png WORKING.png `
  --method edge --tolerance 28 --border 2 `
  --report qa/background_removal.json
```

- **Default to `--method edge`.** It removes only regions connected to the border,
  protecting an eye, gem or highlight that shares the backdrop colour.
- Use `--method global` only when you can see that the subject contains no
  backdrop-like colour and the background is uniformly keyed.
- Use `--colour "#00ff00"` when the source has a known chroma colour.
- Inspect the mask preview (`--mask-preview mask.png`) before accepting a
  destructive result.
- If the subject touches the canvas edge, fix the crop first; a border-connected
  removal can eat into the subject.

### 3. Clean alpha

```powershell
python tools/clean_transparency.py WORKING.png CLEAN.png `
  --min-island 4 --alpha-floor 2 `
  --report qa/alpha_cleanup.json
```

- `min-island` is deliberately small; a 2px sparkle may be intentional.
- The report lists every removed component. Review it.
- Use `--fill-holes` only for genuine enclosed transparent holes, not for gaps
  that should remain transparent.
- `--smooth` is for soft effects, not pixel art.

### 4. Crop and pad

- Trim to the visible subject only when the animation plan allows each frame to
  have a different bbox. For animation, normally align frames later on a shared
  canvas instead of trimming each one independently.
- Preserve deliberate padding. A sprite that touches the canvas edge will fail
  the default QA gate.
- `tools/resize_sprite.py --fit` preserves aspect ratio and pads to the requested
  canvas. Omit `--no-upscale` only when upscaling is intended.

### 5. Resize

```powershell
# Pixel art
python tools/resize_sprite.py CLEAN.png FINAL.png --scale 2 --method nearest

# Painted art inside a fixed canvas
python tools/resize_sprite.py CLEAN.png FINAL.png --width 512 --height 512 `
  --fit --method lanczos --anchor center
```

For RGBA resizes, the pipeline premultiplies alpha first to avoid dark fringes,
then unpremultiplies. Nearest-neighbour bypasses that path because pixel art must
stay exact.

### 6. Align to the pivot

```powershell
python tools/align_frames.py WORKING_FRAMES ALIGNED_FRAMES `
  --canvas-width 64 --canvas-height 64 `
  --pivot-x 32 --pivot-y 60 --align bottom-center
```

- Use bottom-centre for grounded characters.
- Use `--no-align-y` for jump/fall frames where vertical motion is intentional.
- The tool refuses to silently clip art unless `--allow-clip` is passed.

### 7. Validate and record

```powershell
python tools/validate_sprite.py FINAL.png --spec BRIEF.yaml `
  --report qa/final_technical.json
```

Check dimensions, alpha, padding, pivot, palette and naming. Save the processing
report next to the final asset.

## Output

- `assets/working/<asset_id>/...` for in-progress work
- `assets/approved/<asset_id>/frames/...` only after review
- Background mask, inspect report and alpha-cleanup report under `qa/`
- Final provenance sidecar and manifest entry

## Handoff

Send final frames, pivot, canvas size, processing reports and any deliberate
exceptions to `animation`, `quality-assurance` and `sprite-sheet-production`.

## Quality gate

- [ ] Source was inspected before editing.
- [ ] Background removal was edge-aware by default.
- [ ] Alpha islands/holes were reviewed, not blindly deleted.
- [ ] Resampling matches the style.
- [ ] Canvas, pivot and padding match the brief.
- [ ] Final image passes technical validation.

## Pitfalls

- Global colour-key removal eating an eye or highlight.
- Trimming each animation frame independently, causing jitter.
- Lanczos-resizing pixel art.
- Deleting a 2px sparkle as an "island".
- Filling holes that should remain transparent.
- Saving over the approved source instead of working under `assets/working/`.
