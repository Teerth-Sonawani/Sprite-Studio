# Troubleshooting

## Environment

### `python` is not recognized

Use the Python launcher on Windows:

```powershell
py --version
py tools/inspect_image.py image.png
```

Or install Python 3.10+ and ensure it is on `PATH`.

### `ModuleNotFoundError: PIL` / `yaml` / `numpy`

```powershell
py -m pip install -r requirements.txt
```

or:

```powershell
py -m pip install -e .
```

The core pipeline needs Pillow, PyYAML and NumPy. `jsonschema`, `pytest`,
`imageio` and `imageio-ffmpeg` are optional but recommended.

### MP4 export fails

`preview_animation.py` supports GIF, APNG and WebP without FFmpeg. MP4/WebM needs
`imageio` plus `imageio-ffmpeg`:

```powershell
py -m pip install imageio imageio-ffmpeg
```

If it still fails, use `.gif` or `.png` (APNG); the pipeline does not require
video.

### `aseprite` export is refused

That is intentional. Native `.aseprite` writing is not implemented. Export PNG
frames/sheets and open them in Aseprite.

## Image processing

### Background removal leaves a halo or fringe

- Lower `--tolerance` and check `--mask-preview`.
- The background may be textured; use a cleaner backdrop or a manual mask.
- Anti-aliased edges carry blended backdrop colour; a targeted despill or manual
  edge cleanup may be needed.
- Do not keep eroding the sprite until the silhouette disappears.

### Background removal cuts into the subject

- The subject touches the canvas edge, so the flood fill connected it.
- The subject contains the backdrop colour (white eyes, green gem).
- Raise the backdrop separation in the generation (green/blue chroma) or mask
  manually.
- Try `--method edge` (default) instead of `global`.

### `clean_transparency.py` removed a detail

- Restore from the source.
- Lower `--min-island` (or set 0) and inspect the report.
- A deliberate 1-2px sparkle is not noise; preserve it.
- Do not use `--smooth` on pixel art.

### Resized pixel art is blurry

Use `--method nearest`. Never use Lanczos/bicubic on pixel art unless the art
style explicitly allows it. For integer scaling use `--scale 2` (or 3/4).

### Resized painted art has dark fringes

The built-in RGBA resize premultiplies alpha. If fringing persists, the source
has contaminated edge pixels; inspect and despill the source, then resize.
Do not repeatedly resize back and forth.

### Dimensions are wrong after processing

Generators rarely honour exact dimensions. Inspect actual size, then resize
explicitly. Use `--fit` to preserve aspect ratio and pad to the target. Do not
stretch a character to fit a square canvas.

## Animation

### Frames jitter

Likely per-frame tight cropping. Re-run alignment from the original canvas-sized
frames:

```powershell
py tools/align_frames.py frames/ working/aligned `
  --canvas-width 64 --canvas-height 64 --pivot-x 32 --pivot-y 60
```

### Jump/fall frames are flattened

`align_frames.py` aligns the lowest pixel to the pivot by default. For
intentional vertical motion use `--no-align-y` or keep the authored canvas and
use `--align none`.

### Character shrinks or grows between frames

Use `--scale-mode match_first` or `fit_height` only after inspecting the result.
Forcing bbox height can destroy squash/stretch. If the provider cannot maintain
scale, regenerate the offending frames or composite/repaint from the base.

### Loop pops

Inspect the last-to-first transition. Adjust the first/last pose or timing.
Check the preview at the intended fps. A loop difference metric is a warning, not
proof; watch the animation.

### GIF colours look wrong

GIF uses a limited palette and binary transparency. Use APNG (`.png`) or WebP for
colour fidelity, or inspect the source frames. Do not judge palette accuracy from
a GIF alone.

## Sprite sheets

### Cells are cut off

The declared grid does not fit the sheet. Check `--columns`, `--rows`,
`--cell-width`, `--cell-height`, margin and spacing. The tool refuses invalid
grids; read the error. Do not guess a different grid and assume it is right.

### Engine shows the wrong frames

- Filename order may be lexicographic (`frame10` before `frame2`).
- The sidecar may use a different origin than the engine.
- The sheet may have empty cells that were skipped.
- The engine may expect columns/rows, not rects.

Use zero-padded names and make the sidecar authoritative.

### Tile seam warning

Inspect the 2x2 wrap and 3x3 assembled preview. A high seam ratio may be
acceptable for a stylised boundary, but a visible repeat line is a defect. Fix
the edge pixels or redesign the tile; do not hide it with blur.

### Isometric tiles don't connect

Check footprint, height, projection angle and anchor. A visually good tile with
the wrong footprint is unusable. Validate the assembled grid before approval.

## QA and manifests

### `validate_sprite.py` fails on padding

The subject touches the canvas edge. Increase the canvas, re-align, or crop the
source with padding. Do not set `--allow-edge-contact` just to silence the check
unless the asset is intentionally full-bleed (for example a background).

### `validate_sprite.py` fails on transparency

The file is RGB or has no transparent pixels. Remove the background and save RGBA.
An RGBA file with no transparent pixels still fails a transparency-required brief.

### Manifest says `PENDING`

No QA report was supplied. Run technical validation, then a visual review, then
regenerate the manifest with `--qa-report`.

### Export refuses because QA is not APPROVED

That is the intended gate. Complete visual review with evidence, or use
`--allow-unapproved` for a demo build only. Do not edit the manifest status by
hand.

### Schema validation fails

Read the error. Common causes: missing `manifest_version`, invalid `qa_status`,
or a file record without a 64-character SHA-256. Regenerate the manifest rather
than hand-patching hashes.

## Perchance

### `PERCHANCEAI_API_KEY is required`

Set the environment variable in the same shell:

```powershell
$env:PERCHANCEAI_API_KEY = "pca_live_..."
```

Do not put it in a tracked file. Verify:

```powershell
py tools/generate_asset.py health --provider perchance --mode developer_api
```

### `Model ... is not in the current catalog`

Run `models` and use the exact returned `model_key`. Do not guess or use a
provider's upstream model name.

### Estimate fails with 401

The key is missing, invalid, expired or revoked. Recreate it in the PerchanceAI
account UI. No query token or cookie fallback is supported.

### Generation says approval required

Review the estimate, then pass `--confirm`. The default approval gate is
intentional.

### Generation says budget exceeded

Raise `--budget-credits` or choose a cheaper model, but only after reviewing the
actual estimate. Do not disable the limit to "make it work".

### Submission uncertain

The adapter saves the idempotency key and refuses to blindly retry. Check the
account/task status; retry only with the same key and identical payload if the
service supports it. Do not create a new key for an uncertain submission.

### `documented_tutorial` mode is unsupported

The tutorial's endpoint returned HTTP 404 in testing. Use `developer_api` or
`manual`. See `docs/PERCHANCE_INTEGRATION.md`.

### Manual handoff does not fill the prompt

It is not supposed to. Manual mode writes a prompt file and instructions; you
paste it into the browser. This preserves the provider's terms and avoids
automating a challenge-protected interface.

## Tests

### Tests fail because fixtures are missing

```powershell
py tests/fixtures/make_fixtures.py
py -m pytest -q
```

### A test needs network/credentials

Live provider tests are skipped by default. Do not make ordinary test runs spend
credits. Set explicit opt-in environment variables if you intentionally run live
checks.
