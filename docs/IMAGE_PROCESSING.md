# Image Processing

The generator produces a picture. The pipeline produces a game asset. This
document explains what the tools do, what they deliberately do not do, and how to
avoid destroying artwork while cleaning it.

## 1. Preserve the source

Never overwrite an original generation or an approved asset. Keep:

```text
assets/source/       original downloaded/generated files + prompt/provenance
assets/working/      processed candidates
assets/approved/     reviewed, approved deliverables
assets/rejected/     rejected candidates kept for comparison
```

Every processing step writes a new file and a report. Hashing (`sha256`) lets you
prove which source produced which output.

## 2. Inspect first

```powershell
python tools/inspect_image.py source.png --palette --max-colors 24
```

Record:

- actual dimensions (generators rarely obey exact sizes);
- mode (RGB vs RGBA);
- alpha coverage and bbox;
- number of frames (GIF/WebP);
- palette;
- hash.

Do not assume an image has transparency because the prompt asked for it. Many
generators return a checkerboard, white, green or gradient background.

## 3. Background removal

`tools/remove_background.py` defaults to an **edge-connected** method:

1. Sample border colours (coarse clusters, not one pixel).
2. Build a colour-distance mask.
3. Flood-fill from the border only.
4. Remove the connected backdrop.
5. Report border residual and visible pixels.

Why edge-connected? A global colour key removes every matching pixel, including
eyes, gems, highlights or fabric that happens to match the backdrop. Edge-connected
removal is safer for artwork.

Options:

- `--tolerance`: RGB distance; raise for noisy/JPEG backgrounds, lower for tight
  chroma.
- `--border`: sample width.
- `--colour`: explicit backdrop colour(s), repeatable.
- `--method global`: remove every matching pixel. Use only when you have checked
  the subject has no matching colours.
- `--method none`: inspect the sampled background without changing the image.
- `--feather`: soften the cut; use sparingly (can create halos).
- `--alpha-floor`: zero near-transparent noise.
- `--mask-preview`: inspect exactly what was removed.

```powershell
python tools/remove_background.py source.png working/subject.png `
  --tolerance 24 --border 2 --mask-preview working/subject_mask.png `
  --report working/subject_bg.json
```

### Limitations

- Textured or photographic backgrounds may not be one connected colour region.
- A subject touching the canvas edge can be incorrectly connected to the
  background.
- Semi-transparent hair, smoke, glass and water need manual alpha work or a
  dedicated matting tool.
- Chroma spill (green fringe) may remain; inspect and despill locally.
- Do not blindly remove every pixel of a colour. Check the mask preview.

If the result has a fringe, try a tighter tolerance, a different backdrop, or a
manual mask. Do not repeatedly erode the sprite until the silhouette disappears.

## 4. Transparency cleanup

```powershell
python tools/clean_transparency.py working/subject.png working/subject_clean.png `
  --min-island 4 --report working/subject_clean.json
```

The tool removes visible connected components smaller than `min_island` and lists
each removed component. It preserves the largest component by default.

- A 2-pixel sparkle may be intentional. Use a small threshold and inspect.
- `--fill-holes` fills enclosed transparent regions; use for accidental pinholes,
  not for genuine holes (eyes, handles, gaps).
- `--smooth` blurs alpha; avoid on pixel art and crisp vector art.
- Do not apply a global alpha threshold to soft painted edges unless the style
  requires it.

## 5. Cropping and padding

- Crop only empty margins, not "to the subject" for animation frames.
- Keep a consistent canvas for all frames in an animation.
- Preserve intentional shadows, hair, antennae, weapons and effects.
- Add padding for engine filtering and to avoid clipping at sprite bounds.
- For UI icons, keep consistent optical padding across the set.

`tools/resize_sprite.py --fit` preserves aspect ratio inside a target box and pads
to the exact canvas. Without `--fit`, exact width/height can distort; use that
only when the brief explicitly allows it.

## 6. Resizing

| Art | Method | Why |
|---|---|---|
| Pixel art | `nearest` | preserves hard pixels; no invented colours |
| Flat vector | `lanczos` or `bicubic` | clean downscale |
| Painted | `lanczos` | preserves detail; alpha-aware premultiplication |
| UI icons | `nearest` for pixel UI, `lanczos` for painted UI | match the style |

The RGBA resizer premultiplies alpha for non-nearest methods to avoid dark
fringes from hidden RGB under transparent pixels. It never uses integer scaling
implicitly; request `--scale` when you need exact 2x/3x/4x.

Never upscale pixel art with Lanczos and call it "HD". If the style needs a larger
canvas, redraw or use integer nearest scaling with a documented reason.

## 7. Colour management

- Extract palettes with `tools/palette_check.py`.
- Compare to the project palette and record the worst distance.
- Quantize only when the style requires a palette limit; preserve alpha.
- Quantization can destroy anti-aliasing and subtle shading. Inspect the result.
- Do not use palette reduction to hide inconsistent lighting; fix the asset.

## 8. Cleaning defects

Detect and correct:

- isolated opaque pixels;
- background remnants at edges;
- accidental marks;
- broken edges;
- unexpected transparency inside the subject;
- inconsistent borders;
- compression artefacts.

Context matters. A single pixel can be an eye highlight; a cluster of random
pixels is likely noise. Use the mask preview, the alpha report and a zoomed
contact sheet. Do not auto-delete small details without inspecting them.

## 9. Resampling and alpha

Pillow resizes straight alpha; hidden RGB in transparent areas can bleed into
edges. The built-in `resize_rgba` avoids this for smooth resampling. For pixel art,
nearest-neighbour sidesteps the issue entirely.

WebP/PNG preserve alpha; JPEG does not. Do not use JPEG for sprites unless the
target platform explicitly requires it and the asset has no transparency.

## 10. Processing report

Every processing command should write a report with:

- input/output paths and hashes;
- method and parameters;
- removed pixel counts;
- border residual;
- alpha bbox;
- warnings.

Store reports under `qa/` or beside the working asset. If a result is questioned
later, the report explains what happened.

## 11. What not to do

- Do not overwrite `approved/`.
- Do not remove a background by deleting every pixel of one colour without
  checking the subject.
- Do not apply Lanczos to pixel art.
- Do not crop animation frames independently to their content.
- Do not use a high-quality downscale to "fix" a silhouette that is unreadable at
  game size; redesign the silhouette.
- Do not claim transparency was verified just because the file is RGBA; check the
  alpha channel.
