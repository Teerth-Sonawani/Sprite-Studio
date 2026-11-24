# Agent Operating Rules

This file is mandatory context for any agent working in this workspace. Read it
before touching assets, prompts, manifests or exports.

## 1. Non-negotiable rules

1. **Do not skip planning.** Convert an underspecified request into an explicit
   asset brief. Record assumptions instead of silently inventing them.
2. **Freeze the style before producing a set.** Reuse
   `projects/<project>/style_guide.yaml`; do not re-invent a style per asset.
3. **Generation is not delivery.** A generated image is a candidate until it has
   been inspected, processed, validated and visually reviewed.
4. **Never claim approval without evidence.** Technical checks can only reach
   `TECHNICAL_PASS`. `APPROVED` requires a separate visual review with evidence
   paths. `human_approved` is independent of AI review.
5. **Keep provenance.** Record provider, mode, exact model key, prompt file,
   parameters, generation id, source hash and output paths.
6. **Never put credentials in tracked files, prompts, URLs, logs or manifests.**
   Read `PERCHANCEAI_API_KEY` from the environment only.
7. **Do not create or imitate protected characters, logos or a living artist's
   signature style.** Describe visual characteristics instead.
8. **Respect the cost gate.** Estimate before generating; require `--confirm` for
   chargeable requests; never retry an uncertain POST with a new idempotency key.
9. **Do not overstate integrations.** Perchance Mode A is unsupported (HTTP 404
   evidence). Aseprite native writing is not implemented. Say so.
10. **Preserve user work.** Inspect unfamiliar files before overwriting or
    deleting them. Use `--overwrite`/`--force` deliberately.

## 2. Read order

1. `README.md`
2. This file
3. `docs/WORKFLOW.md`
4. `projects/<project>/project_brief.md`
5. `projects/<project>/style_guide.md` and `style_guide.yaml`
6. `config/quality_profiles.yaml` and `config/export_profiles.yaml`
7. Existing asset manifests and QA reports

If a request conflicts with these files, stop and surface the conflict.

## 3. Status lifecycle

```text
PENDING -> TECHNICAL_PASS -> VISUAL_REVIEW -> APPROVED
                     \-> REJECTED
VISUAL_REVIEW -> revise (stays VISUAL_REVIEW) -> APPROVED / REJECTED
```

| Status | Meaning | May export? |
|---|---|---|
| `PENDING` | Created, not technically validated | No |
| `TECHNICAL_PASS` | Deterministic checks passed; no visual review | No, unless explicitly demo |
| `VISUAL_REVIEW` | Reviewer inspected evidence and requested changes, or marked demo/internal | Only with `--allow-unapproved` and a demo label |
| `APPROVED` | Technical pass + recorded visual approval | Yes, within the approval scope |
| `REJECTED` | Failed a gate; do not ship as production | No |

`APPROVED` with `reviewer_type: ai_agent` is scoped to `demo_or_internal`.
Production release requires `human_approved: true` unless the project brief
explicitly says otherwise.

## 4. Phase checklist

### Plan

- [ ] Asset id, category and subcategory are explicit.
- [ ] Canvas size, display size, pivot and ground contact are explicit.
- [ ] Transparency, animation and export requirements are explicit.
- [ ] The brief validates against `schemas/asset_brief.schema.json`.
- [ ] Dependencies and references are listed.

### Generate

- [ ] Prompt was built from the brief and frozen style guide.
- [ ] Provider, mode, model key and parameters are recorded.
- [ ] Estimate was reviewed and is within budget.
- [ ] `--confirm` is present only for an approved charge.
- [ ] Source candidates are preserved under `assets/source/`.

### Process

- [ ] Source inspected with `tools/inspect_image.py`.
- [ ] Background removed edge-aware, not by an indiscriminate global key.
- [ ] Alpha islands and holes handled deliberately.
- [ ] Resampling matches the style (nearest for pixel art).
- [ ] Frames share a canvas and pivot.
- [ ] Processing report saved.

### Animate

- [ ] Animation spec exists before frames are produced.
- [ ] Frame count, fps, loop and durations match the spec.
- [ ] Feet/ground contact or centre is stable, except intentional motion.
- [ ] Preview exists at intended display size.
- [ ] `tools/validate_animation.py` does not report `FAIL`.

### Validate

- [ ] Technical report exists and passed critical checks.
- [ ] Contact sheet and preview exist.
- [ ] Visual review records reviewer, type, scores, notes and evidence.
- [ ] Approval scope is recorded honestly.
- [ ] Manifest reflects the latest QA report.

### Export

- [ ] Manifest is `APPROVED` (or the export is explicitly demo-only).
- [ ] Every manifest file exists and its hash matches.
- [ ] Export profile matches the engine.
- [ ] Engine import was verified in the engine, not just by file existence.
- [ ] Export is reproducible from the manifest and sources.

## 5. File and naming rules

- Asset ids: `[A-Za-z0-9_.-]+`, lowercase snake_case preferred.
- Frame names: `<asset_id>__<animation>__frame_<NNN>.png`.
- Sheet names: `<asset_id>__<animation>__sheet.png`.
- Preview names: `<asset_id>__<animation>__preview.gif`.
- Manifest names: `<asset_id>.manifest.json`.
- Keep source candidates; never delete rejected work without a recorded reason.
- `assets/approved/` is for reviewed work only. `assets/working/` is for
  in-progress output. `assets/source/` is immutable provenance.
- Exports are generated artifacts; never hand-edit an export and call it source.

## 6. Provider rules

### Supported modes

| Provider | Mode | What happens |
|---|---|---|
| `mock` | `offline` | Deterministic local geometry for tests/dry runs. No network. |
| `perchance` | `manual` | Writes prompt, prompt sidecar and browser handoff. Human imports the result. |
| `perchance` | `developer_api` | Documented PerchanceAI developer API. Requires a formal key and approval for charges. |
| `perchance` | `documented_tutorial` | Raises `UnsupportedIntegration`; endpoint returned HTTP 404 on 2026-11-12. |

### Hard provider rules

- Discover models with `models`; never hardcode or guess a model key.
- Validate parameters against the selected model's `input_schema`.
- Do not send the bearer token to signed output URLs or third-party hosts.
- Save the idempotency key and record before submitting a chargeable request.
- On an uncertain submission, stop and require a human to check status. Do not
  resubmit with a fresh key.
- A successful API response proves a task completed, not that the art is good.

## 7. Tool map

| Task | Command |
|---|---|
| Inspect | `python tools/inspect_image.py IMAGE --palette` |
| Validate one sprite | `python tools/validate_sprite.py IMAGE --spec SPEC --report QA` |
| Remove backdrop | `python tools/remove_background.py IN OUT --report QA` |
| Clean alpha | `python tools/clean_transparency.py IN OUT --report QA` |
| Resize/canvas | `python tools/resize_sprite.py IN OUT --width W --height H [--fit]` |
| Align frames | `python tools/align_frames.py FRAMES OUT --canvas-width W --canvas-height H --pivot-x X --pivot-y Y` |
| Slice sheet | `python tools/slice_spritesheet.py SHEET --columns N --rows M --out-dir DIR` |
| Build sheet | `python tools/build_spritesheet.py FRAMES --output SHEET --metadata JSON --layout horizontal` |
| Contact sheet | `python tools/make_contact_sheet.py FRAMES --output PNG --title TITLE` |
| Preview animation | `python tools/preview_animation.py FRAMES --output PREVIEW.gif --frames-per-second N` |
| Validate animation | `python tools/validate_animation.py FRAMES --expected-count N --report QA` |
| Palette check | `python tools/palette_check.py IMAGE --limit N --compare PALETTE` |
| Tile seam check | `python tools/tile_seam_check.py TILE --assembled PREVIEW --report QA` |
| Pack atlas | `python tools/pack_atlas.py FRAMES --output PNG --metadata JSON` |
| Build prompt | `python tools/build_prompt.py BRIEF --style STYLE --output PROMPT.txt` |
| Generate | `python tools/generate_asset.py generate --provider P --mode M ...` |
| Import manual result | `python tools/import_generated.py IMAGE --dest DIR --asset-id ID` |
| Build manifest | `python tools/generate_manifest.py ASSET_DIR --brief BRIEF --style STYLE --qa-report QA --output MANIFEST` |
| Record visual review | `python tools/qa_review.py QA --decision approve --reviewer NAME --evidence PREVIEW --output REVIEW` |
| Export | `python tools/export_asset.py MANIFEST --profile PROFILE --out DIR` |

Run a tool with `--help` for its exact flags.

## 8. Handoffs

Pass structured files, not vague prose. A handoff should include:

```yaml
from: prompt_engineer
to: generation_specialist
asset_id: character_moss_slime_01
brief: projects/example-project/assets/briefs/moss_slime.yaml
style: projects/example-project/style_guide.yaml
prompt_file: projects/example-project/assets/source/prompts/moss_slime_idle.prompt.txt
model_key: "<discovered at runtime>"
candidates: 3
max_credits: 30
acceptance:
  - single subject
  - transparent or chroma background
  - readable at 32px
```

For a revision, name the defect, the frame, the evidence path and the requested
correction. Do not send "make it better".

## 9. Failure handling

- **Technical failure:** fix the file or the spec, re-run the check, keep the old
  report for comparison.
- **Visual revision:** correct locally (one frame, fringe, palette) before
  regenerating the whole asset.
- **Repeated failure:** diagnose the cause. Check prompt ambiguity, reference
  inconsistency, canvas mismatch, provider limitations, or an impossible style
  request. Stop after the project's correction-round limit.
- **Provider error:** preserve the record, do not expose the key, and do not retry
  a chargeable uncertain request automatically.
- **Missing dependency:** the tool must fail with a clear message. Do not silently
  substitute a lower-quality path.

## 10. Definition of done

An asset is done only when:

- the brief and style are recorded;
- final frames share a canvas and pivot;
- technical QA passed;
- visual QA has evidence and an honest approval scope;
- the manifest validates and every file hash is current;
- the requested export exists and was imported/verified in the target engine;
- known limitations and next actions are reported without exaggeration.
