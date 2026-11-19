# Animation

Animation is a production subsystem, not a by-product of generating several
images. The hard problems are identity, placement, timing and loop quality.

## 1. Choose a production strategy

| Strategy | Good for | Risk |
|---|---|---|
| Individually generated frames | expressive poses, painted styles | identity drift, scale drift |
| Reference-conditioned frames | characters with a strong approved design | provider may still ignore details |
| Keyframe + in-between construction | pixel art, controlled motion | manual effort, limited perspective changes |
| Sprite-sheet generation | simple effects, icons, uniform grids | cells often inconsistent; must be sliced and inspected |
| Transform/composite of a base | blink, bob, squash, simple props, UI | can look mechanical if overused |

Do not assume a generated "walk cycle sheet" is usable. Inspect every cell.

## 2. Write the animation spec before frames

Use `templates/animation_spec.yaml`. At minimum:

- frame count, frame rate, loop/once;
- canvas size and pivot;
- direction and movement description;
- per-frame pose, duration and notes;
- transition requirements;
- visual constraints;
- sheet layout.

Frame counts are configurable. A 4-frame idle and a 12-frame run can coexist.
Do not force every animation into the same count.

## 3. Preserve identity

1. Approve a canonical base design first.
2. Put the reference path in the brief and animation spec.
3. Pass the reference to the provider when supported.
4. State fixed features (eye spacing, fern side, costume) and variable features
   (limb pose).
5. Compare every frame to the base, not only to the previous frame.
6. If the provider cannot maintain identity, construct the animation from a base
   with controlled transforms or repaint the problem areas. Do not claim
   consistency you did not verify.

Common identity defects:

- head/body ratio changes;
- eye spacing or pupil size changes;
- costume details disappear;
- outline thickness changes;
- palette shifts between frames;
- handedness changes without a story reason;
- fern/antenna/hair asymmetry flips.

## 4. Alignment

All frames in one animation must have:

- identical canvas dimensions;
- a consistent pivot;
- consistent character scale;
- appropriate ground contact or intentional airborne offset;
- transparent padding;
- no unintended clipping.

Use:

```powershell
python tools/align_frames.py path/to/frames working/aligned `
  --canvas-width 64 --canvas-height 64 `
  --pivot-x 32 --pivot-y 60 `
  --align bottom-center
```

For jump/fall, pass `--no-align-y` so vertical movement is preserved. For
inconsistent generated frames, `--scale-mode fit_height` can normalise height,
but inspect the result: forcing every bbox to the same height can remove genuine
squash/stretch.

Do not crop each frame tightly to its own content. That destroys positional
motion and makes the animation jitter.

## 5. Timing

- Use per-frame durations when the motion needs them; the tools support lists.
- A looping idle at 6 fps is not the same as a walk at 12 fps.
- Preview at the intended fps, not at the generation tool's default.
- Fast effects need higher rates; slow ambience can use fewer frames.
- GIF previews can quantize colours; use APNG/WebP or inspect the source frames
  when colour fidelity matters.

## 6. Loops

For looping animations, inspect the last-to-first transition especially:

- Does the pose lead into frame 0?
- Does the body jump position?
- Does a limb duplicate or skip a phase?
- Does the palette or brightness flicker?
- Does a scrolling tile seam show?

`tools/validate_animation.py` reports a loop difference score. It is a warning,
not proof of quality. Watch the preview.

## 7. Validation

Run:

```powershell
python tools/validate_animation.py working/aligned `
  --expected-count 6 --width 64 --height 64 `
  --pivot-x 32 --pivot-y 60 `
  --report qa/walk_animation_report.json
```

Checks:

- expected count and canvas size;
- empty frames;
- identical or near-identical adjacent frames;
- centre displacement;
- height/scale variation;
- mean-colour drift;
- loop difference;
- opaque pixels touching the canvas edge;
- durations present and positive.

Then create a contact sheet and an animated preview:

```powershell
python tools/make_contact_sheet.py working/aligned --output qa/walk_contact.png --title "Moss Slime walk"
python tools/preview_animation.py working/aligned --output qa/walk_preview.gif --frames-per-second 10
```

Inspect the contact sheet frame by frame and the preview in motion. At least one
preview must show the asset at its intended in-game size.

## 8. Frame generation discipline

- Generate the approved base first.
- For each frame, specify the phase and the fixed features.
- Do not generate frame n+3 before frame n is accepted if the frames depend on
  each other; sequential work is often cheaper than reconciling drift.
- Keep rejected frames when they explain a correction.
- If a single frame is bad, fix that frame. Do not regenerate a whole animation
  just because one pose failed.
- If the whole design is wrong, stop and revise the brief/style, not the prompt
  wording alone.

## 9. Animation types

The registry includes character, creature, object, environment, UI and effect
animations. See `config/animation_presets.yaml`. Presets are starting points;
override frame count, rate and loop per project.

Examples:

- **Character:** idle, walk, run, jump, fall, land, turn, climb, swim, interact,
  sleep, celebrate, expressions, emotes.
- **Creature:** idle, walk, run, fly, swim, turn, eat, sleep, emote.
- **Object:** spin, rotate, open, close, blink, float, pulse, mechanism.
- **Environment:** flowing water, foliage sway, clouds, rain, snow, ambient light.
- **UI:** button states, hover, pressed, loading, notification, progress.
- **Effects:** particles, dust, bubbles, sparkles, smoke, light, ambient.

## 10. Export timing metadata

Record per animation:

- frame count;
- frame rate;
- loop/once;
- per-frame durations when non-uniform;
- sheet region or frame filenames;
- pivot;
- notes about intentional vertical motion.

The manifest and sheet sidecar must agree. If they disagree, the engine will
play the wrong animation even if the images look correct.

## 11. Failure modes and fixes

| Symptom | Likely cause | Targeted fix |
|---|---|---|
| Character grows/shrinks | independent generation, no scale lock | align/scale to base height; regenerate only offending frames |
| Eyes flicker | face redrawn each frame | repaint eyes from reference; lock eye spacing |
| Animation jitters | per-frame tight cropping | align on pivot, re-export |
| Feet slide | inconsistent ground contact | align bottom-centre; check baseline |
| Loop pops | last pose not leading to first | adjust first/last poses or timing |
| Colour pulsing | palette drift | palette-check; map to project palette |
| Limb disappears | cropping or generation defect | increase canvas/padding; repaint/regenerate frame |
| Sheet cells bleed | no spacing/incorrect cell size | add spacing, validate grid, rebuild sheet |
