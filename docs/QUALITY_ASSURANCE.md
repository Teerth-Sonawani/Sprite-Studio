# Quality Assurance

No asset is approved because an AI says it "looks good." QA is split into
deterministic technical checks, visual evidence and explicit approval state.

## 1. Status model

```text
PENDING
TECHNICAL_PASS
VISUAL_REVIEW
APPROVED
REJECTED
```

- **PENDING** — created, not validated.
- **TECHNICAL_PASS** — automated checks passed; no visual sign-off.
- **VISUAL_REVIEW** — a reviewer inspected evidence and either requested changes
  or approved for demo/internal use.
- **APPROVED** — technical pass plus a recorded approval. The manifest separately
  records `human_approved`; production release requires human sign-off unless
  the project explicitly states otherwise.
- **REJECTED** — do not export as production.

A high visual score never overrides a critical technical failure. A critical
failure can be fixed and re-run; it cannot be voted away.

## 2. Technical validation

```powershell
python tools/validate_sprite.py path/to/sprite.png `
  --width 64 --height 64 --transparency --padding 2 `
  --pivot-x 32 --pivot-y 60 `
  --report qa/sprite_technical.json
```

| Test | Requirement |
|---|---|
| File integrity | image opens completely |
| Dimensions | match the brief/canvas |
| Colour mode | appropriate RGB/RGBA/indexed |
| Transparency | correctly implemented where required |
| Empty content | at least one visible pixel |
| Cropping | subject does not unintentionally touch the edge |
| Padding | follows the asset specification |
| Pivot | inside the canvas and matches the brief |
| File naming | follows the naming convention |
| Palette | within the declared limit/compare threshold |
| File size | within the export profile limit |
| Sprite sheet | declared grid, cells fit, frames present |
| Animation | frame count, order, dimensions, loop |
| Manifest | required fields, QA consistency, schema |
| Export | compatible with the selected profile |

The tool never emits `APPROVED`; that is a separate review record.

## 3. Visual validation

The reviewer must examine the actual image and at least one in-context preview.
Check:

- silhouette readability at intended game size;
- subject recognition and role;
- visual clarity and edge quality;
- shape/proportion consistency;
- perspective consistency;
- lighting consistency;
- palette consistency;
- texture/material quality;
- unwanted artefacts (fringes, halos, stray pixels, duplicated limbs);
- cropping;
- in-game readability against a representative background;
- animation smoothness and loop;
- style-guide compliance.

### Evidence

Approval requires evidence paths that exist, for example:

- contact sheet;
- animated preview;
- in-game-size preview;
- 1x and 2x zoomed crops.

Record the reviewer type (`ai_agent` or `human`), the scores, and notes. Use
`tools/qa_review.py`:

```powershell
python tools/qa_review.py qa/sprite_technical.json `
  --decision approve --reviewer "art-review-agent" --reviewer-type ai_agent `
  --score silhouette=4 --score style=5 --score cleanliness=4 `
  --evidence qa/sprite_contact.png --evidence qa/sprite_preview.gif `
  --notes "Reads at 32px; fern intact; no fringe." `
  --output qa/sprite_review.json
```

An agent approval is recorded as `human_approved: false` and scoped to
`demo_or_internal`. A human approval is recorded as `human_approved: true`. Do
not change the reviewer type to bypass this distinction.

## 4. In-game usability testing

Do not judge only at generation resolution.

- Produce previews at the actual display size.
- Test on light, dark and busy backgrounds.
- Compare relative scale with characters, doors, tiles and UI.
- Check contrast; a sprite can be beautiful and invisible in the scene.
- For UI, test at 24px and 32px and at the target DPI.
- For animation, preview at the intended fps and inspect the loop seam.
- For tiles, assemble a 3x3 grid and inspect the repeat.
- For VFX, check that the effect does not obscure gameplay or UI.

## 5. Defect reporting

Every rejection should identify:

- asset/frame;
- defect with a location;
- why it matters in game;
- severity;
- targeted correction;
- evidence.

Example:

```text
asset: character_moss_slime_01 walk frame 3
defect: right eye shifts outward 2px; eye spacing flickers
impact: identity breaks at 32px
severity: major
fix: repaint eyes from the approved idle reference; keep body pose
evidence: qa/moss_slime_walk_contact_sheet.png
```

"Looks bad" and "AI said it is good" are not QA records.

## 6. Scoring

Optional 0-5 scores for prioritisation:

- silhouette / readability;
- identity / consistency;
- style compliance;
- cleanliness / artefacts;
- animation / motion;
- in-game usability.

Guidance:

- 5: production-ready for its use;
- 4: minor issues, may pass with notes;
- 3: visible issues, revision needed;
- 2: major issues, rework;
- 1: unusable, reject.

Scores are prioritisation, not permission. A critical technical failure blocks
approval regardless of a 4.9 average.

## 7. Manifest QA state

`tools/generate_manifest.py` reads the QA report. It does not fabricate approval.
If no report is supplied, the manifest is `PENDING`.

```json
"qa": {
  "technical_status": "TECHNICAL_PASS",
  "visual_status": "APPROVED",
  "qa_status": "APPROVED",
  "human_approved": false,
  "report": "qa/sprite_review.json",
  "review": {
    "decision": "approve",
    "reviewer": "art-review-agent",
    "reviewer_type": "ai_agent",
    "approval_scope": "demo_or_internal"
  }
}
```

Export refuses a non-approved manifest unless `--allow-unapproved` is used for a
demo build. Never ship an `--allow-unapproved` export as production.

## 8. Release checklist

- [ ] Brief and style guide were followed.
- [ ] Technical report is `TECHNICAL_PASS`.
- [ ] Visual review evidence exists.
- [ ] Animation preview and loop were inspected.
- [ ] In-game-size preview was inspected.
- [ ] Palette and outline match the project.
- [ ] Tiles assemble; UI states align.
- [ ] Manifest validates against the schema.
- [ ] Provenance and licence are recorded.
- [ ] Export profile matches the target engine.
- [ ] `human_approved` is true for production release.
- [ ] Rejected candidates are preserved, not mixed into approved.

## 9. What can be automated

Automate dimensions, alpha, bbox, padding, palette counts, seam metrics, frame
count, duplicate detection, displacement, scale variation, loop difference,
manifest schema, hashes, naming and export file lists.

Do not automate:

- whether the character is recognisable;
- whether the pose is appealing;
- whether the asset fits the game's tone;
- whether a copyrighted design was accidentally reproduced;
- whether a loop reads well in motion.

Those require looking, and sometimes a human.

## 10. Sample QA artifacts

The example project contains:

```text
projects/example-project/qa/moss_slime_technical.json
projects/example-project/qa/moss_slime_review.json
projects/example-project/qa/moss_slime_idle_contact.png
projects/example-project/qa/moss_slime_idle_preview.gif
projects/example-project/qa/grass_seam_report.json
projects/example-project/qa/grass_assembled_3x3.png
```

These are demo assets generated procedurally for the workspace, not commissioned
production art. Their review records state that clearly.
