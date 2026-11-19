---
name: character-design
description: Design consistent 2D characters and creatures with a readable silhouette, character sheet, expression and variant plan, and animation-ready proportions.
---

# Character Design

## Purpose

Turn a character concept into a reusable, animation-ready design that stays
consistent across poses, expressions, palettes and sizes.

## Use when

- Designing a player character, NPC, creature, enemy or portrait.
- A character changes between frames or animations.
- Building palette swaps, costumes, damage states or expressions.
- A design must read at gameplay size, not only in a large illustration.

## Inputs

- Project brief and frozen style guide
- Asset brief for the character
- Approved reference character, if any
- `config/asset_categories.yaml` (character subcategories)
- `templates/character_sheet.yaml`

## Procedure

1. **Write the role in one sentence.** Who is this, what do they do, and how
   should the player recognise them at a glance?
2. **Define the silhouette.** Choose two or three shape cues (round, angular,
   tall, low, horned, floating). If the silhouette is not distinct in solid
   black, redesign before adding detail.
3. **Set proportions and scale.** Record total height, head/body ratio, eye line,
   foot width and the ground contact point. Keep them in a character sheet.
4. **Build the palette.** Assign base, shadow, highlight, outline, eye, accent and
   material colours. State how many colours each material may use.
5. **Design the face and readability.** Eyes and mouth must survive at the target
   game size. Avoid facial detail that disappears below 32px.
6. **Define the costume and props.** Record what moves, what is rigid and what is
   attached. State which props are separate sprites.
7. **Draw the canonical pose first.** The idle or neutral pose becomes the
   reference. Do not start with an extreme action pose.
8. **Plan expressions and variants.** List eyes, mouth, blink, hurt, happy, angry,
   palette swap, costume and damage states. Note which share geometry.
9. **Plan animation constraints.** Foot contact, body bob, pivot, hair/cloth
   motion and which limbs should separate. For creatures, define how the body
   squashes and stretches.
10. **Create a character sheet.** Front/side/back or the required views, head
    close-up, palette strip and silhouette test. Include annotation arrows for
    asymmetrical features.
11. **Test at game size.** Downsample to the intended display size and inspect the
    silhouette and face. If it fails, simplify.
12. **Review against the style guide.** Check outline, palette, lighting,
    perspective and detail density. Record any approved deviation.

## Output

- `projects/<project>/assets/briefs/<character_id>.yaml`
- `projects/<project>/assets/source/concepts/<character_id>_concept.png`
- `projects/<project>/references/<character_id>_sheet.png`
- A character sheet YAML/Markdown with proportions, palette and variant notes.

## Handoff

Send the selected concept, character sheet, pivot and palette to
`image-processing` and `animation`. Send the silhouette test and style
comparison to `quality-assurance`.

## Quality gate

- [ ] Silhouette reads in one colour at game size.
- [ ] Proportions and pivot are recorded and consistent.
- [ ] Palette roles and limits are explicit.
- [ ] Face reads at the smallest target size.
- [ ] Animation constraints are documented.
- [ ] No protected character or franchise likeness.

## Pitfalls

- Designing a detailed illustration that becomes mush at 32px.
- Changing proportions between idle and walk.
- Baking props into the body when they should be separate sprites.
- Using pure black outlines in a palette that specifies hue-shifted darks.
- Adding asymmetrical detail without a front/side reference.
