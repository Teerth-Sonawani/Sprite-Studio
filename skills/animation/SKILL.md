---
name: animation
description: Specify, align, preview and validate 2D frame animations with stable identity, timing, pivots, loop seams and intentional vertical motion.
---

# Animation

## Purpose

Produce animations that are readable in motion, stable across frames and
technically valid for the target engine.

## Use when

- A character, creature, object, environment or UI element needs frames.
- Frames drift, jitter, change size or lose identity.
- An animation loops badly or has incorrect timing.
- A preview or sheet is needed for review or export.

## Inputs

- Asset brief with animation list
- `templates/animation_spec.yaml`
- `config/animation_presets.yaml`
- Aligned frames (or source frames to align)
- Project fps and engine conventions

## Procedure

### 1. Write the spec before the frames

Record:

- animation name and id;
- frame count, fps and per-frame durations (if non-uniform);
- loop type (`loop`, `once`, `ping-pong`) and whether the last frame repeats the
  first;
- direction and alignment (bottom-centre, centre, tile);
- movement description and ground contact;
- which frames are key poses (contact, down, passing, up);
- intentional vertical motion for jump/fall.

Use a preset as a starting point. Override it per asset; do not treat it as law.

### 2. Produce or select frames

- Keep the same canvas and pivot for every frame.
- Do not independently crop each frame to its own bounding box.
- For squash/stretch, keep the silhouette anchored at the ground contact.
- For jump/fall, preserve the authored vertical arc instead of forcing feet to
  the baseline.
- For VFX, define how alpha and brightness change over the loop.

### 3. Align

```powershell
python tools/align_frames.py RAW_FRAMES ALIGNED_FRAMES `
  --canvas-width 64 --canvas-height 64 `
  --pivot-x 32 --pivot-y 60 --align bottom-center
```

Use `--no-align-y` for jump/fall. The tool reports offsets and refuses silent
clipping.

### 4. Build a preview at intended size

```powershell
python tools/preview_animation.py ALIGNED_FRAMES `
  --output qa/moss_slime_idle_preview.gif `
  --frames-per-second 6 --background checker --overwrite
```

- Check the preview at 1x and the actual in-game size.
- GIF is flattened; APNG/WebP preserve alpha.
- MP4/WebM require `imageio` + `imageio-ffmpeg`; system FFmpeg is optional.

### 5. Validate

```powershell
python tools/validate_animation.py ALIGNED_FRAMES `
  --expected-count 4 --width 64 --height 64 `
  --pivot-x 32 --pivot-y 60 `
  --report qa/moss_slime_idle_animation.json
```

The validator checks frame count, canvas size, empty frames, duplicate frames,
centre displacement, height variation, palette drift, loop seam, edge artefacts,
durations and pivot. It returns `PASS`, `WARN` or `FAIL`. Warnings are
diagnostics, not automatic approval.

### 6. Inspect visually

- Identity: same character, palette, outline and proportions.
- Motion: readable arc, contact and passing poses, no unintended jitter.
- Loop: last-to-first transition is as smooth as any interior transition.
- Ground contact: feet stay planted unless the motion intends lift.
- Effects: alpha falloff and brightness do not flicker unintentionally.
- Gameplay: the animation does not obscure hitboxes, UI or other actors.

### 7. Build a contact sheet

```powershell
python tools/make_contact_sheet.py ALIGNED_FRAMES `
  --output qa/moss_slime_idle_contact.png --columns 4 `
  --title "Moss Slime - Idle" --overwrite
```

Review frames side by side. A looping preview can hide a bad individual frame.

## Output

- `animations/<asset_id>__<animation>.yaml` spec
- Aligned PNG frames
- `qa/<asset_id>__<animation>__preview.gif` (or APNG/WebP)
- `qa/<asset_id>__<animation>__contact.png`
- `qa/<asset_id>__<animation>__validation.json`

## Handoff

Send the spec, frames, preview, contact sheet and validation report to
`sprite-sheet-production` and `quality-assurance`.

## Quality gate

- [ ] Spec exists and matches the frames.
- [ ] All frames share a canvas and pivot.
- [ ] No empty or accidental duplicate frames.
- [ ] Identity and palette are stable.
- [ ] Loop seam is inspected.
- [ ] Preview exists at intended display size.
- [ ] Validator is not `FAIL`; warnings are explained.

## Pitfalls

- Generating frames at different sizes and calling it animation.
- Forcing jump/fall feet to the same baseline.
- Trusting a looping GIF without inspecting individual frames.
- Using a 512px preview to judge a 32px asset.
- Ignoring a loop warning because the still frames look fine.
- Assuming a provider generated consistent frames; it usually did not.
