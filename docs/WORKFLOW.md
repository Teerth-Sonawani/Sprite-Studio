# Workflow

This document defines the operating sequence for every asset task. The order is
deliberate: generation is one step, not the whole job.

## Roles at a glance

| Role | Primary output | May approve? |
|---|---|---|
| Asset Planner | asset brief, dependency list, technical spec | no |
| Art Director | frozen style guide, reference board, compliance notes | style compliance only |
| Prompt Engineer | provider-ready prompt, negative prompt, reference plan | no |
| Generation Specialist | source candidates, provider/model/prompt provenance | no |
| Image Processing Specialist | cleaned RGBA frames, masks, processing reports | technical pass only |
| Animation Specialist | aligned frames, timing, sheet, preview | no |
| Quality Inspector | technical report, visual review, defect list | yes, per status rules |
| Export Specialist | engine package, manifest, import notes | no |

One agent may perform several roles sequentially. Do not spawn agents just to
imitate an org chart. When a handoff is needed, pass structured files (YAML/JSON,
image paths, reports), not a vague sentence.

## Phase 1 — Understand

Read, in this order:

1. The project brief (`projects/<project>/project_brief.md`).
2. The frozen style guide (`style_guide.md` and `style_guide.yaml`).
3. The target engine/export profile.
4. The specific request and any existing manifests.

Write down unknowns. If the request is underspecified (for example "a knight" for
a 16x16 UI slot), ask or choose an explicit, documented assumption.

**Output:** understood constraints, open questions, project paths.

## Phase 2 — Plan

Create an asset brief from `templates/asset_brief.yaml`. Determine:

- one asset id and category/subcategory;
- final display size and canvas size;
- transparency, pivot, ground contact;
- animation list and dependencies;
- whether the asset must share a reference with existing assets;
- validation profile and export profile.

Check `config/asset_categories.yaml` and `config/quality_profiles.yaml`. If the
category does not exist, add it rather than misclassifying the asset.

**Output:** validated `asset_brief.yaml`.

## Phase 3 — Establish references

Find the approved base reference. For a character this is the canonical idle;
for a tile it is the approved tile family; for UI it is the icon grid and palette.
If no reference exists, the first asset in the family becomes the reference only
after visual review.

Record the reference path in the brief. Do not generate a "family" from unrelated
one-off prompts.

**Output:** reference paths and a short consistency note.

## Phase 4 — Design

Make concept candidates at low cost. Compare:

- silhouette at final game size;
- category/role readability;
- fit with the style guide;
- technical feasibility (single subject, clean edges, no baked background).

Choose one direction and record why. Rejected concepts stay in `source/concepts/`
or `rejected/` when useful for comparison. Do not keep generating after the
direction is settled.

**Output:** selected concept/concept direction.

## Phase 5 — Generate

Build the prompt with `tools/build_prompt.py` or the provider handoff. Follow
`docs/PERCHANCE_INTEGRATION.md`.

Record before submitting:

- provider, mode, exact model key;
- prompt file and negative prompt;
- requested parameters and dimensions;
- cost estimate and approval;
- reference upload ids, if any.

Generate a configurable number of candidates (default 3). Every extra candidate
needs a reason. Preserve originals under `assets/source/`.

**Output:** source images + generation record + provenance.

## Phase 6 — Process

Do not treat the generator's output as game-ready.

1. Inspect: `tools/inspect_image.py`.
2. Remove the backdrop with an edge-aware method: `tools/remove_background.py`.
3. Clean alpha islands: `tools/clean_transparency.py`.
4. Crop/trim with intentional padding.
5. Resize with the right resampler: nearest for pixel art, Lanczos for painted.
6. Align to the pivot.
7. Save under `assets/working/`; never overwrite `approved/`.

**Output:** processed RGBA candidate(s) + processing report.

## Phase 7 — Animate

Write the animation spec first (`templates/animation_spec.yaml`), then produce
frames. Align frames with `tools/align_frames.py`; do not independently crop each
frame to its own bounding box. For jump/fall, preserve authored vertical motion.

Build a sheet and preview, then validate:

```text
tools/build_spritesheet.py
tools/preview_animation.py
tools/validate_animation.py
```

**Output:** frames, sheet, preview, animation validation report.

## Phase 8 — Validate

Two separate gates:

1. **Technical:** dimensions, alpha, padding, pivot, palette, naming, sheet grid,
   animation consistency. `tools/validate_sprite.py`, `tools/validate_animation.py`.
2. **Visual:** inspect the contact sheet and the in-game-size preview. Check
   silhouette, identity, perspective, lighting, edges and style compliance.

Create at least one preview at the actual intended display size. A 512px render
that only reads at 512px is not a 32px game asset.

**Output:** technical QA report + visual review record.

## Phase 9 — Correct

Prefer local corrections:

- stray pixel -> clean/repair, not regenerate;
- background fringe -> alpha/despill fix;
- one bad frame -> regenerate or repaint that frame;
- scale mismatch -> align/scale with a documented reason;
- whole design wrong -> new concept, new generation.

Limit correction rounds (default 3). If an asset keeps failing, diagnose the
cause: prompt ambiguity, provider limitation, inconsistent reference, wrong
canvas, or an impossible style/size request. Do not loop blindly.

**Output:** corrected asset + defect-resolution note.

## Phase 10 — Export

Only export after the manifest's QA state permits it. Create:

- individual frames;
- sprite sheet(s) with sidecar metadata;
- preview and contact sheet;
- manifest with provenance;
- engine package via `tools/export_asset.py`.

Approved assets live under `assets/approved/`; exports are generated artifacts
and may be rebuilt. Do not hand-edit an export and call it the source of truth.

**Output:** export package + manifest.

## Phase 11 — Deliver

Report concisely:

- what was created;
- file locations;
- dimensions and pivot;
- animation names, frame counts, rates and loop behaviour;
- export formats;
- QA status and whether a human approved it;
- known limitations and required next action.

Never report a rejected or unreviewed file as approved.

## Status lifecycle

```text
PENDING -> TECHNICAL_PASS -> VISUAL_REVIEW -> APPROVED
                     \-> REJECTED
VISUAL_REVIEW -> REVISE (stays VISUAL_REVIEW) -> APPROVED/REJECTED
```

- `TECHNICAL_PASS`: deterministic checks passed; no visual sign-off.
- `VISUAL_REVIEW`: a reviewer inspected evidence and requested changes, or an
  agent approved for demo/internal use.
- `APPROVED`: technical pass + recorded visual approval. `human_approved` is a
  separate boolean; production release requires a human unless the project
  explicitly says otherwise.
- `REJECTED`: do not export as production.

## Handoff format

Use a small structured handoff, for example:

```yaml
from: prompt_engineer
to: generation_specialist
asset_id: character_moss_slime_01
prompt_file: assets/source/prompts/moss_slime_idle.prompt.txt
model_key: flux-2.0
candidates: 3
max_credits: 30
reference: assets/approved/moss_slime/frames/moss_slime__idle__frame_000.png
acceptance:
  - single subject
  - transparent or chroma background
  - readable at 32px
```

## Efficiency rules

- Reuse the project style guide; do not re-derive it per asset.
- Reuse approved references and prompt patterns.
- Cache generation metadata; hash source files.
- Generate alternatives only where selection is genuinely uncertain.
- Do not regenerate an approved asset without a documented reason.
- Correct locally before regenerating globally.
- Keep the pipeline engine-independent; export at the end.
