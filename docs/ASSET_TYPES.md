# Asset Types

The taxonomy is extensible. `config/asset_categories.yaml` is the registry; each
category has defaults and a QA profile. Add categories rather than forcing an
asset into the wrong shape.

## Characters and living assets

**Subcategories:** main character, NPC, creature, animal, enemy, variation,
portrait, expression.

Required decisions:

- final display height and canvas size;
- pivot and ground contact;
- canonical reference;
- animation set;
- silhouette differentiation from other characters;
- whether the asset is mirrored or has a dedicated left/right version.

Character-specific checks:

- proportions and eye spacing stable across frames;
- feet/base at a consistent ground line (except intentional jump/fall motion);
- readable face at in-game size;
- equipment/held items aligned to the hand pivot;
- no soft drop shadow baked into the sprite unless the style explicitly does it.

## Environment art

**Subcategories:** terrain, ground tile, wall, platform, building, background,
plant, tree, rock, water surface, interior, exterior, autotile, isometric tile.

Required decisions:

- tile size and grid;
- camera/perspective;
- parallax layer role;
- whether the asset is a single object or a repeating tile;
- connection rules (edges, corners, autotile bitmask);
- colour/value relationship to the foreground.

Environment-specific checks:

- seam continuity for repeating tiles;
- assembled 3x3 preview inspected, not just the single tile;
- scale relative to characters and doors;
- background value contrast does not compete with gameplay;
- isometric footprint/height consistent with the grid.

## Objects and props

**Subcategories:** furniture, food, collectible, container, decorative,
interactive, transportation, weapon, held item.

Required decisions:

- pivot (especially for held items);
- whether the object has states (closed/open, off/on, full/empty);
- whether it needs an animation (spin, blink, open, float);
- collision footprint versus visual footprint.

## UI assets

**Subcategories:** button, icon, panel, HUD component, menu, inventory slot,
cursor, indicator, loading animation.

Required decisions:

- final display size, not just source size;
- state set (normal/hover/pressed/disabled/selected);
- safe padding and nine-slice borders;
- contrast against the busiest intended background;
- font/text policy (text is normally rendered by the engine, not baked in).

UI-specific checks:

- test at 24px and 32px for icons;
- state variants align pixel-for-pixel;
- consistent optical weight across an icon set;
- no unreadable micro-detail;
- transparent padding is intentional and consistent.

## Visual effects

**Subcategories:** dust, cloud, rain, snow, water ripple, bubble, sparkle, light
effect, smoke, particle, ambient.

Required decisions:

- blend mode (alpha, additive, additive-with-alpha);
- frame count, rate, loop/one-shot;
- whether the effect tiles or is screen-aligned;
- brightness range and how it reads over light/dark scenes;
- whether the effect obscures gameplay.

VFX-specific checks:

- loop seam and brightness flicker;
- alpha falloff preserved;
- no hard rectangular background;
- preview at intended fps;
- effect does not hide the player, hazards or UI.

## Animation metadata

Animation is both a category and a cross-cutting concern. Character, creature,
object, environment, UI and effect animations use the same animation schema but
different QA profiles. See `docs/ANIMATION.md`.

## Adding a category

1. Add a block to `config/asset_categories.yaml` with defaults and a `qa_profile`.
2. Add or reuse a profile in `config/quality_profiles.yaml`.
3. Add a style-compatible brief template if the category has unique fields.
4. Document the technical requirements in this file.
5. Add a test fixture only if the new category needs validation logic, not just
   taxonomy.

Unknown fields in briefs and manifests are preserved. Do not rewrite the core
pipeline to add a category.

## Scale reference

Record a table in the project style guide. Example:

| Asset | Display size | Canvas | Notes |
|---|---:|---:|---|
| Player slime | 32px tall | 64x64 | pivot bottom-centre |
| NPC | 48px tall | 96x96 | pivot bottom-centre |
| Door | 64px tall | 64x96 | bottom-centre |
| Ground tile | 32x32 | 32x32 | seamless |
| UI icon | 24px | 32x32 | 4px padding |
| HUD panel | 320x48 | 320x48 | nine-slice |
| VFX sparkle | 32x32 | 32x32 | additive |

If an asset cannot be measured against this table, the brief is incomplete.
