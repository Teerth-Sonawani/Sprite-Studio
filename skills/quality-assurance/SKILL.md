---
name: quality-assurance
description: Run deterministic technical checks, evidence-backed visual reviews and manifest validation without confusing AI approval with human sign-off.
---

# Quality Assurance

## Purpose

Decide whether an asset is usable, with evidence and a recorded scope. QA is not
a rubber stamp and not a single AI opinion.

## Use when

- Any asset, frame set, sheet, tile or export is about to be approved.
- A defect must be documented and sent back for correction.
- A manifest needs a current QA status.
- A release needs to know whether human sign-off exists.

## Inputs

- Asset file(s), sheet and preview
- Asset brief and style guide
- `config/quality_profiles.yaml`
- `schemas/asset_manifest.schema.json`
- Existing technical and visual reports

## Two gates

### Gate 1 — Technical

```powershell
python tools/validate_sprite.py FINAL.png `
  --spec projects/example-project/assets/briefs/moss_slime.yaml `
  --report qa/moss_slime_technical.json
```

Checks can include file integrity, dimensions, mode, transparency, empty content,
padding, edge contact, pivot, naming, palette limit, file size and coverage.
Critical failures mean `REJECTED`; all critical checks passing means
`TECHNICAL_PASS`.

This gate **never** produces `APPROVED`.

For animations:

```powershell
python tools/validate_animation.py FRAMES --expected-count 4 `
  --width 64 --height 64 --pivot-x 32 --pivot-y 60 `
  --report qa/moss_slime_animation.json
```

For tiles, run `tools/tile_seam_check.py` and inspect the assembled preview.

### Gate 2 — Visual

Create evidence at the intended display size:

- labelled contact sheet;
- animated preview;
- 1x and 2x crops;
- in-context preview (light/dark/busy background);
- tile 3x3 assembly;
- sheet with cell boundaries if relevant.

Inspect:

- silhouette and subject recognition;
- identity and proportion consistency;
- edge quality, fringes, halos and stray pixels;
- palette and lighting consistency;
- perspective and scale;
- face/detail readability at game size;
- animation motion, ground contact and loop seam;
- style-guide compliance;
- gameplay readability.

Record the review:

```powershell
python tools/qa_review.py qa/moss_slime_technical.json `
  --decision approve `
  --reviewer "art-review-agent" --reviewer-type ai_agent `
  --score silhouette=4 --score style=5 --score cleanliness=4 `
  --evidence qa/moss_slime_contact.png `
  --evidence qa/moss_slime_idle_preview.gif `
  --notes "Reads at 32px; fern intact; no fringe." `
  --output qa/moss_slime_review.json
```

An AI approval becomes `qa_status: APPROVED`, `reviewer_type: ai_agent`,
`approval_scope: demo_or_internal`, `human_approved: false`. A human approval
sets `human_approved: true` and production scope.

Do not change reviewer type to bypass the distinction.

## Status rules

| Outcome | Status |
|---|---|
| Not checked | `PENDING` |
| Critical technical checks pass | `TECHNICAL_PASS` |
| Visual revision requested | `VISUAL_REVIEW` |
| Technical pass + recorded approval | `APPROVED` |
| Critical failure or visual rejection | `REJECTED` |

A high visual score never overrides a critical technical failure.

## Manifest validation

```powershell
python tools/generate_manifest.py ASSET_DIR `
  --brief BRIEF --style STYLE --animations animations `
  --qa-report qa/moss_slime_review.json `
  --provider procedural_demo --mode offline `
  --notes "Original procedural demo art; not AI-generated." `
  --output manifests/moss_slime.manifest.json --force
```

Verify:

- required fields and JSON Schema;
- every file path exists;
- every hash is current;
- QA status is internally consistent;
- `APPROVED` has a technical pass and evidence;
- `human_approved` is not implied by AI review;
- provenance states the real provider/mode/model, including "procedural demo".

## Defect report format

```yaml
asset_id: character_moss_slime_01
frame: 2
defect: dark fringe on the left silhouette
location: x=14..22, y=31..46
why_it_matters: reads as a dirty outline at 32px
evidence: qa/moss_slime_contact.png
requested_fix: edge-aware alpha cleanup, not a full regeneration
severity: major
```

## Output

- `qa/<asset_id>_technical.json`
- `qa/<asset_id>_review.json`
- Contact sheet, preview, seam report and any comparison images
- Updated manifest

## Quality gate

- [ ] Technical report exists and is current.
- [ ] Visual evidence exists and was actually inspected.
- [ ] Reviewer, type, scores, notes and evidence are recorded.
- [ ] Approval scope is honest.
- [ ] Manifest validates and hashes match.
- [ ] Known limitations are listed.

## Pitfalls

- Approving from a filename or a thumbnail.
- Treating a warning as a pass without explanation.
- Approving a 512px render that fails at 32px.
- Marking `human_approved: true` from an AI review.
- Letting a manifest point at an older file version.
- Calling a candidate "perfect" instead of listing its remaining defects.
