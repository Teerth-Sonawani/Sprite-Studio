# Changelog

All notable changes to this workspace. Dates are ISO 8601.

## [Unreleased]

### Added

- GitHub repository preparation: `LICENSE`, `CONTRIBUTING.md`,
  `CODE_OF_CONDUCT.md`, `SECURITY.md`, `SUPPORT.md`, issue and pull-request
  templates, Dependabot configuration, a CI workflow, `.editorconfig` and
  `.gitattributes`.
- GitHub-oriented README with example previews, installation, usage,
  documentation links and honest limitations.
- CI matrix for Ubuntu and Windows on Python 3.10-3.12, plus a demo-build and
  manifest-hash verification job.

### Changed

- `.gitignore` now keeps the checked-in example MP4, ignores the local agent
  harness directory and covers additional coverage/cache artifacts.
- `pyproject.toml` includes the project license files in built distributions.

### Notes

- No git remote is configured and nothing has been pushed.

## [1.0.0] - 2026-11-12

Final packaging and verification pass: 2026-11-13.

### Added

- Complete agent workflow: planning, art direction, generation, processing,
  animation, QA and export.
- Reusable `sprite_studio` Python package with 20 thin CLI tools.
- Edge-connected background removal, alpha-island cleanup, premultiplied resize,
  palette extraction, frame alignment, preview generation and animation QA.
- Sprite-sheet slicing and assembly, contact sheets, shelf atlas packing and tile
  seam diagnostics.
- Asset briefs, style guides, animation specs and project briefs with JSON
  Schemas.
- Extensible registries for 13 art styles, asset categories, animation presets,
  quality profiles and export profiles.
- Provider abstraction with a deterministic mock provider and a Perchance
  adapter supporting manual handoff and the documented PerchanceAI developer API.
- Evidence-backed QA records that keep `human_approved` separate from AI review.
- Generic PNG, Godot 4 and Unity 2022 exports, plus an honest refusal for native
  Aseprite writing.
- Eleven focused skills, root operating rules and a worked example project.
- Reproducible procedural demo assets: moss slime idle/walk, seamless grass tile,
  UI sparkle icon and sparkle VFX.
- Unit, integration and acceptance tests.

### Verified

- `GET https://api.perchanceai.art/api/v1/developer/models` returned HTTP 200
  with 47 models (19 image, 28 video) during the build.
- `POST /generations/estimate` without a token returned
  `401 DEVELOPER_TOKEN_REQUIRED`.
- `GET https://perchance.org/api/generateList.php?...` returned HTTP 404.
- `python -m pytest -q`: **98 passed, 1 warning** in about 10-11 s. The warning
  comes from the third-party `anyio` pytest plugin, not project code.
- `python scripts/build_demo_assets.py --stage all`: four assets reached
  `TECHNICAL_PASS`, four AI review records were applied, six export jobs were
  built, and manifest hash verification passed for 36 files.
- All four example manifests validate and report `APPROVED` with
  `human_approved: false`.

### Not done / limitations

- No charged PerchanceAI generation; no credentials were available.
- Perchance reference upload and conditioning were not exercised live.
- Godot and Unity artifacts were generated and structurally validated, but not
  opened in the applications.
- Native Aseprite/LibreSprite project writing is not implemented.
- Example art is procedural demo art, not AI-generated and not a quality
  showcase for any provider.
- Human art review was not available; demo approvals are AI-reviewed and scoped
  to `demo_or_internal`.

### Fixed during the build

- Manifest file paths are now relative to the manifest folder and portable
  alongside exports.
- Godot `.tres` sub-resources are emitted before `[resource]`, with a correct
  `load_steps` count and unique IDs.
- Sprite-sheet `--keep-empty` now actually writes empty cells.
- Sprite-sheet assembly uses natural filename order.
- Atlas packing validates item size against the maximum dimensions.
- Palette quantisation no longer counts colours hidden under alpha=0.
- Mock provider creation no longer passes unsupported options.
- Perchance documentation no longer shows the invalid `generate --estimate`
  flag combination.
- Background-mask arithmetic uses `int32` to avoid `int16` overflow on
  multi-megapixel images.
- Native-alpha VFX frames are aligned with `--align none` so transparent
  expansion is not clipped.
- The slime aggregate QA summary now covers only its own two animations; the
  intentional `sparkle_vfx` scale-variation warning is reported on that asset.
- Animated GIF previews are discovered and included in manifests; `qa.report`
  paths are stored relative to the manifest folder.
- Anchor aliases such as `bottom-center`, `top-center`, `center-left` and
  `center-right` are accepted alongside the original underscore names.
