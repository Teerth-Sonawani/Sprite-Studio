# Art Direction

Art direction is a project-level contract. It exists so that asset #37 looks like
it belongs with asset #1. A prompt is not a style guide, and a style guide is not
a mood board with no measurable rules.

## 1. Freeze a style guide before production

Copy `templates/style_guide.yaml` into the project and fill it out. It must define:

- style family/id and a one-paragraph description;
- line art: outline width, colour, interior-line policy;
- palette: maximum colours, swatches, temperature;
- shading: highlight/shadow logic and texture policy;
- lighting: direction and contrast;
- perspective and camera;
- proportions and scale relationships;
- detail density and pixel-grid policy;
- recommended canvas sizes and export settings;
- prompt modifiers, negative modifiers and processing rules;
- approved references.

The machine-readable YAML is used by the prompt builder and manifests. The
human-readable `style_guide.md` explains the *why* and shows examples.

## 2. Consistency rules

- **Palette:** do not invent a new palette per asset. Variants must be declared
  and derived from the base.
- **Camera:** do not change angle without a documented reason. A side-view game
  does not get a 3/4 hero asset unless the UI explicitly needs it.
- **Outline:** keep the same width and hue logic. An outline that disappears on
  dark backgrounds is a defect, not a stylistic surprise.
- **Lighting:** one consistent key direction per scene family. Rim lights are a
  deliberate choice, not a random addition.
- **Detail:** match the detail budget. A 32px character cannot carry 12px of
  facial rendering.
- **Scale:** record real relationships (door height, player height, tile size).
  Validate assets side by side.
- **Materials:** wood, metal, cloth and moss should read consistently across
  assets. Reuse shading recipes.
- **References:** keep an approved reference image per family and pass it to the
  generator when supported.

## 3. Silhouette first

At game size, silhouette carries recognition. Test:

1. Fill the sprite with a single colour on a mid-value background.
2. View at the intended display size (not the generation resolution).
3. Check that the role is readable: player vs enemy vs pickup vs background.
4. Only then judge interior detail.

If two characters have the same silhouette, differentiate shape, not just colour.

## 4. Value structure

- Characters and interactables need enough contrast against the environment.
- Backgrounds should recede: lower contrast, cooler/darker as depth increases.
- UI must remain legible over the busiest scene. Test over a representative
  background, not a flat grey rectangle.
- Do not rely on hue alone; value and shape must also separate.

## 5. Perspective and camera

Record the projection explicitly:

- side-on orthographic;
- 3/4 top-down;
- isometric 2:1 or true isometric;
- straight-on UI.

For tiles and isometric assets, the grid is part of the style. Verify footprint
and height against the grid before judging surface detail. A tile that looks good
alone but breaks when assembled is not art-direction compliant.

## 6. Palette management

- Keep a project palette file and approved variants.
- Extract palettes with `tools/palette_check.py`; compare generated assets to the
  approved palette.
- Palette limits are style decisions. A 24-colour pixel style should not quietly
  become a 300-colour render.
- Anti-aliasing introduces intermediate colours. If the style forbids it, reject
  or process the asset rather than pretending the palette still holds.
- Preserve important accent colours (eyes, UI state, danger) even when reducing.

## 7. Originality and ethics

- Do not reproduce existing copyrighted characters, logos, costumes or sprites.
- Do not ask for a named living artist's style. Describe visual characteristics
  instead.
- Do not use a franchise name as shorthand for a design. Write the actual visual
  requirements.
- Record the source, provider, model and licence status for every asset.
- If a generated output accidentally resembles a known protected design, reject
  it and change the brief.

## 8. Reviewing candidates

Score against the brief, not personal taste:

| Criterion | Question |
|---|---|
| Silhouette | Is the role readable at game size? |
| Identity | Does it match the approved reference/character bible? |
| Style | Palette, outline, shading and detail budget consistent? |
| Camera | Correct view and perspective? |
| Composition | Entire asset visible, sensible padding? |
| Technical | Single subject, clean edges, no baked background? |
| Usability | Does it work in the intended scene/UI? |

A candidate can be beautiful and still fail. Reject it and say which criterion
failed; "looks bad" is not a usable defect report.

## 9. Writing a defect report

Include:

- asset id and frame;
- what is wrong (specific region);
- why it matters in game;
- severity (critical / major / minor);
- recommended targeted correction;
- evidence path (contact sheet/preview).

Example:

```text
asset: character_moss_slime_01 walk frame 3
defect: right eye shifts 2px outward; left eye stays anchored
impact: eye spacing flickers at 32px, breaking identity
severity: major
fix: repaint frame 3 eyes from the approved idle reference; do not regenerate the whole walk
evidence: qa/moss_slime_walk_contact_sheet.png
```

## 10. When to revise the style guide

Revise only for a project-level decision, not to excuse one bad asset. Record the
change, the reason and which existing assets need review. If the change affects a
shipped asset, re-run its technical and visual checks.
