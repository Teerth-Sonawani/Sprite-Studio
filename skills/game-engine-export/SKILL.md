---
name: game-engine-export
description: Package approved 2D assets for generic engines, Godot 4 or Unity 2022, with manifests, sidecars, pivots, import notes and honest limitations.
---

# Game Engine Export

## Purpose

Turn an approved asset into a reproducible engine package. Export is generated
from the manifest; it is never the source of truth.

## Use when

- Delivering frames, sheets or atlases to an engine.
- Creating a Godot `SpriteFrames` resource.
- Preparing Unity slicing metadata.
- Writing generic PNG/JSON interchange files.
- Rebuilding an export after a source or QA change.

## Inputs

- Approved manifest (or explicit demo approval)
- Sprite sheets + sidecars
- Animation specs with timing and loop flags
- Pivot/ground-contact convention
- `config/export_profiles.yaml`
- Target engine version and import settings

## Export profiles

| Profile | Writes | Honest limitation |
|---|---|---|
| `generic_png` | frame PNGs by role, self-contained manifest, animations.json | Engine import is project-specific |
| `generic_sheet` | sheet PNG, copy/manifest with sidecar paths, animations.json | Sidecar is authoritative |
| `godot_4` | sheets, `SpriteFrames` `.tres`, import notes | Verify in Godot; regenerate after sheet changes |
| `unity_2022` | sheet, `.slices.json`, `.meta` template, import notes | JSON is an import recipe, not a native `.asset` |
| `aseprite` | refuses; no native `.aseprite` writer | Open PNG frames in Aseprite instead |

## Procedure

### 1. Verify approval and manifest

```powershell
python tools/export_asset.py manifests/moss_slime.manifest.json `
  --profile godot_4 --out exports/godot --force
```

A non-`APPROVED` manifest is refused. Use `--allow-unapproved` only for a
clearly labelled demo export.

Before exporting, confirm:

- QA status and scope;
- every manifest file exists;
- hashes are current;
- sheet sidecar matches the sheet;
- animation names, durations and loop flags are correct;
- pivot convention is documented.

### 2. Generic PNG

Use `generic_png` when the engine can load individual textures or you need the
most portable package. The exporter rewrites a self-contained `manifest.json`
whose file paths are relative to the export folder. `animations.json` lists frame
and sheet paths.

### 3. Generic sheet

Use `generic_sheet` when the engine wants a texture + JSON. The sidecar contains:

- sheet dimensions;
- columns, rows, cell size, spacing and margin;
- each frame's actual rect and cell rect;
- durations in milliseconds.

### 4. Godot 4

The exporter writes:

- sheet PNG(s);
- `<asset_id>.tres` with `SpriteFrames`;
- `AtlasTexture` sub-resources for each frame;
- `import_notes.json`.

The `.tres` emits ext/sub-resources before `[resource]` and counts `load_steps`.
It uses the full cell rect so transparent padding keeps alignment. Verify:

- texture filter (Nearest for pixel art, Linear for painted);
- animation names, frame order and loop flags;
- pivot/offset in the scene;
- no blur or bleed on import.

Copy the whole exported folder into the Godot project and keep the `.tres` and
PNGs together. If the sheet is rebuilt, regenerate the `.tres`; do not hand-patch
regions.

### 5. Unity 2022.3+

The exporter writes:

- sheet PNG;
- `<sheet>.slices.json` with rects, animation groups and import settings;
- `<sheet>.png.meta` TextureImporter template;
- `import_notes.json`.

The JSON is an **import recipe**, not native slicing. In Unity:

1. Import the PNG.
2. Set Texture Type to Sprite (2D and UI).
3. Set Sprite Mode to Multiple.
4. Apply the rects in the Sprite Editor or with an editor script.
5. Set Filter Mode to Point for pixel art.
6. Set Pixels Per Unit consistently.
7. Create clips and set loop time per clip.

Review the `.meta` template; Unity may regenerate GUIDs.

### 6. Aseprite

Native `.aseprite` writing is not implemented. The exporter refuses even if a CLI
is found. Export PNG frames/sheets and author layers, tags and timing in the
application. Keep the native file as a separate editable source.

## Coordinates and pivots

- Manifest pivot: pixels from top-left, usually ground contact.
- Godot region: top-left origin.
- Unity pivot: normalized (0-1), usually bottom-centre.
- Generic JSON: top-left origin, pixel rects.

A mismatch causes visible misalignment even when the images are correct.

## Post-export verification

- [ ] Import the package into the real engine.
- [ ] Confirm transparency and filtering.
- [ ] Confirm frame order and animation speed.
- [ ] Confirm loop flags.
- [ ] Confirm pivot/ground contact in a scene.
- [ ] Check at the actual game resolution.
- [ ] Record any engine-specific changes in the project notes.

File existence is not import verification.

## Output

```text
exports/<profile>/
  sheet PNG(s)
  manifest.json (generic profiles)
  animations.json
  <asset_id>.tres (Godot)
  <sheet>.slices.json (Unity)
  <sheet>.png.meta (Unity)
  import_notes.json
```

## Handoff

Send the export folder, manifest, import notes and verification result to the
project owner. Report unverified items explicitly.

## Pitfalls

- Exporting a `TECHNICAL_PASS` asset as production.
- Hand-editing an export and leaving the source/manifest stale.
- Shipping a sheet without its sidecar or vice versa.
- Assuming the Unity `.meta` alone configures slicing.
- Forgetting to set nearest filtering for pixel art.
- Claiming an export "works" without opening the engine.
