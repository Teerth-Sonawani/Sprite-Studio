# Build Report — 2D Sprite Studio

**Build date:** 2026-11-12 (final verification and packaging: 2026-11-13)
**Workspace:** `2d-sprite-studio/`
**Report status:** verified against the files and commands in this workspace; the
final test suite, demo build and quick-start commands were run and checked on
2026-11-13. No unimplemented feature is listed as complete.

---

## 1. Result in one paragraph

The workspace is built and runnable. It provides 20 command-line tools over a
reusable `sprite_studio` Python package, 11 focused skills, extensible YAML
registries, JSON Schemas, 10 documentation guides, a mock provider, a
Perchance manual/developer-API adapter, and a complete example project. The
example project contains four original procedural assets with briefs, animation
specs, processing reports, technical QA, contact sheets, sprite sheets, animated
previews, AI-authored demo-scoped review records, validated manifests and six
export jobs (generic PNG, Godot 4, Unity 2022). The full suite reports
**98 passed, 1 external warning**. The example pipeline reports four
`TECHNICAL_PASS` assets, four applied AI reviews, six completed exports and a
manifest hash verification of 36 files with no errors.

---

## 2. Folder tree

Generated folders (`__pycache__/`, `.pytest_cache/`) are omitted. Binary frames
and exports are summarised rather than listed one by one. `.opencode/` is
harness-managed and not part of the deliverable.

```text
2d-sprite-studio/
├── README.md                     Overview and quick start
├── AGENTS.md                     Mandatory operating rules
├── SKILL.md                      Top-level skill router
├── BUILD_REPORT.md               This report
├── CHANGELOG.md                  Build history
├── LICENSES.md                   Licensing and third-party notices
├── .env.example                  Credential placeholders only
├── .gitignore                    Secrets, caches and local artifacts ignored
├── pyproject.toml                Package metadata and tool config
├── requirements.txt              Runtime and test dependencies
├── conftest.py                   Root pytest path setup
├── config/                       7 registries
│   ├── art_styles.yaml           13 starting styles
│   ├── asset_categories.yaml     Categories and subcategories
│   ├── animation_presets.yaml    Reusable timing presets
│   ├── quality_profiles.yaml     Technical QA thresholds
│   ├── export_profiles.yaml      generic_png, godot_4, unity_2022
│   ├── providers.yaml            Provider capabilities
│   └── studio.yaml               Workspace defaults
├── docs/                         10 guides
│   ├── WORKFLOW.md
│   ├── ART_DIRECTION.md
│   ├── ASSET_TYPES.md
│   ├── IMAGE_PROCESSING.md
│   ├── ANIMATION.md
│   ├── SPRITE_SHEETS.md
│   ├── QUALITY_ASSURANCE.md
│   ├── GAME_ENGINE_EXPORT.md
│   ├── PERCHANCE_INTEGRATION.md
│   └── TROUBLESHOOTING.md
├── schemas/                      4 JSON Schemas
│   ├── asset_brief.schema.json
│   ├── style_guide.schema.json
│   ├── animation.schema.json
│   └── asset_manifest.schema.json
├── skills/                       11 SKILL.md guides
│   ├── asset-planning/
│   ├── art-direction/
│   ├── character-design/
│   ├── environment-art/
│   ├── pixel-art/
│   ├── sprite-generation/
│   ├── image-processing/
│   ├── animation/
│   ├── sprite-sheet-production/
│   ├── quality-assurance/
│   └── game-engine-export/
├── sprite_studio/                Reusable Python package (13 modules)
│   ├── __init__.py
│   ├── errors.py
│   ├── image_utils.py
│   ├── background.py
│   ├── sheets.py
│   ├── animation.py
│   ├── tiling.py
│   ├── atlas.py
│   ├── qa.py
│   ├── manifest.py
│   ├── prompting.py
│   ├── export.py
│   ├── config.py
│   └── cli.py
├── providers/
│   ├── base_provider.py          ImageProvider interface
│   ├── provider_registry.py      Config-driven provider lookup
│   ├── mock/adapter.py           Deterministic offline provider
│   ├── perchance/
│   │   ├── adapter.py            manual, developer_api, documented_tutorial
│   │   ├── configuration.py      Validated provider configuration
│   │   └── tests/                Adapter/configuration tests (no network)
│   └── example-project/          Example provider config
├── tools/                        20 thin CLI entry points
│   ├── inspect_image.py          validate_sprite.py
│   ├── remove_background.py      clean_transparency.py
│   ├── resize_sprite.py          align_frames.py
│   ├── slice_spritesheet.py      build_spritesheet.py
│   ├── make_contact_sheet.py     preview_animation.py
│   ├── validate_animation.py     palette_check.py
│   ├── tile_seam_check.py        pack_atlas.py
│   ├── generate_manifest.py      qa_review.py
│   ├── export_asset.py           build_prompt.py
│   ├── import_generated.py       generate_asset.py
├── templates/                    6 YAML/Markdown starting points
├── references/
│   ├── styles/                   Style selector, Mosslight palette
│   └── examples/                 Brief and art-direction walkthroughs
├── tests/                        10 test modules + shared fixtures
│   ├── conftest.py               Reusable generated mini-asset fixture
│   ├── test_image_utils.py       test_background.py
│   ├── test_animation.py         test_atlas.py
│   ├── test_sheets_and_tiling.py test_qa_and_manifest.py
│   ├── test_export.py            test_prompting.py
│   ├── test_provider_registry.py test_cli_acceptance.py
│   └── fixtures/                 Runtime-generated; README only
├── scripts/
│   └── build_demo_assets.py      Reproducible demo pipeline
└── projects/example-project/
    ├── project_brief.md
    ├── style_guide.md
    ├── style_guide.yaml
    ├── README.md
    ├── animations/               3 animation specs
    ├── assets/
    │   ├── briefs/               4 asset briefs
    │   ├── source/procedural/    18 immutable source frames/tiles/icons
    │   ├── source/prompts/       8 prompt/negative files
    │   ├── working/              Processed frames
    │   ├── approved/             4 approved asset folders
    │   │   ├── moss_slime/       frames/{idle,walk}, previews, spritesheets
    │   │   ├── grass_tile/       frame, previews
    │   │   ├── ui_sparkle/       frame, previews
    │   │   └── sparkle_vfx/      frames, previews, spritesheets
    │   └── rejected/             Empty by design; policy README
    ├── qa/                       Processing, technical, animation and review JSON
    ├── manifests/                4 manifests + build_summary.json
    └── exports/
        ├── generic/              4 per-asset generic exports
        ├── godot/                Sheets + .tres + import notes
        ├── unity/                Sheets + .meta + slice JSON + import notes
        └── previews/             3 GIF previews
```

**File inventory:** 290 files excluding caches — 96 PNG, 57 Python, 46 JSON,
41 Markdown, 21 YAML, 9 GIF, 9 text, 4 WebP, 2 Unity `.meta`, 1 MP4, 1 `.tres`,
plus config/metadata files.

---

## 3. Implemented functionality

| Area | What is implemented | Main entry points |
|---|---|---|
| Inspection and analysis | Size/mode/alpha bounding box, padding, coverage, palette extraction, colour comparison | `inspect_image.py`, `palette_check.py` |
| Background processing | Edge-connected flood removal with tolerance, optional explicit key, feather, despill, alpha-island cleanup, premultiplied resize | `remove_background.py`, `clean_transparency.py`, `resize_sprite.py` |
| Frame alignment | Anchor/pivot alignment, shared canvas, transparent padding, anchor aliases | `align_frames.py` |
| Sheets and atlases | Horizontal/vertical/grid assembly, empty cells, metadata sidecars, slicing, contact sheets, shelf packing | `build_spritesheet.py`, `slice_spritesheet.py`, `make_contact_sheet.py`, `pack_atlas.py` |
| Animation | GIF/APNG/WebP/MP4 previews, natural frame ordering, duration/fps control, count/pivot/bounds/scale validation | `preview_animation.py`, `validate_animation.py` |
| Tiling | Seam metrics, 2x2 assembly and wrap previews | `tile_seam_check.py` |
| QA | Deterministic technical checks, status lifecycle, evidence-backed visual reviews, AI vs human approval separation | `validate_sprite.py`, `qa_review.py` |
| Manifests | Schema validation, relative paths, hashes, sidecars, previews, provenance, portability | `generate_manifest.py` |
| Prompting | Brief + frozen style to structured prompts and negative prompts | `build_prompt.py` |
| Providers | Interface, registry, deterministic mock, Perchance manual handoff and developer API, cost gate | `generate_asset.py`, `import_generated.py`, `providers/` |
| Export | Generic PNG copies, Godot 4 `SpriteFrames` `.tres`, Unity 2022 slices + `.meta`, preview copies, honest Aseprite refusal | `export_asset.py` |
| Extensibility | Data-driven styles, categories, presets, QA and export profiles; custom provider registration | `config/`, `providers/provider_registry.py` |

### QA semantics

- Technical validation can only produce `TECHNICAL_PASS`; it never grants
  `APPROVED`.
- `APPROVED` requires a separate visual review that records reviewer, reviewer
  type, scores, notes and evidence paths.
- `human_approved` is independent and remains `false` for all example assets.
- AI approvals are scoped to `demo_or_internal`.

---

## 4. Example project results

`python scripts/build_demo_assets.py --stage all` output:

```text
Assets rebuilt.
  moss_slime: TECHNICAL_PASS
  sparkle_vfx: TECHNICAL_PASS
  grass_tile: TECHNICAL_PASS
  ui_sparkle: TECHNICAL_PASS
Applied 4 visual review(s).
Exports built.
  moss_slime:generic_png
  moss_slime:godot_4
  moss_slime:unity_2022
  grass_tile:generic_png
  ui_sparkle:generic_png
  sparkle_vfx:generic_png
  manifest hash verification: PASS
```

Checked-in results:

| Asset | Content | QA | Export |
|---|---|---|---|
| `moss_slime` | 4 idle + 6 walk frames, 64x64, pivot (32, 60) | `APPROVED` (AI, demo scope) | generic, Godot, Unity |
| `grass_tile` | 32x32 seamless tile + wrap preview | `APPROVED` (AI, demo scope) | generic |
| `ui_sparkle` | 32x32 transparent icon | `APPROVED` (AI, demo scope) | generic |
| `sparkle_vfx` | 6-frame 64x64 burst + sheet | `APPROVED` (AI, demo scope) | generic |

- `qa/assets_stage_summary.json`: four `TECHNICAL_PASS`.
- `qa/review_decisions.json`: four authored AI review decisions with evidence.
- `manifests/build_summary.json`: six exports, `verification.ok: true`,
  `checked: 36`, `errors: []`.
- `sparkle_vfx` animation validation reports `WARN` for `scale_variation`
  (0.828 vs 0.80). The expansion is intentional and documented in the review;
  the aggregate technical status remains `TECHNICAL_PASS`.

The demo art is original procedural Pillow art, not AI-generated. It validates
the pipeline on real pixels and does not represent provider image quality.

---

## 5. Dependencies and environment

Built and tested on Windows with Python 3.12.4.

| Dependency | Role | Verified version |
|---|---|---|
| Pillow | Required image I/O and raster operations | 13.0.0 |
| PyYAML | Required config, briefs, animations | 6.0.2 |
| NumPy | Required array operations | 2.4.6 |
| jsonschema | Required schema validation | 4.26.0 |
| pytest | Tests | 9.2.0 |
| imageio + imageio-ffmpeg | Optional MP4/WebM previews | imageio 2.36.1, bundled FFmpeg |
| SciPy | Optional faster connected components | 1.18.1 |
| OpenCV | Optional, not required by the current pipeline | 4.11.0 |

`requirements.txt` and `pyproject.toml` declare the project dependencies.
System `ffmpeg` is not required when `imageio-ffmpeg` is installed; this is how
the checked-in MP4 preview was produced.

---

## 6. Perchance integration status

Three modes exist. Only two are usable.

| Mode | Status | Evidence |
|---|---|---|
| A — `documented_tutorial` | **Not usable / unsupported** | `GET https://perchance.org/api/generateList.php?...` returned **HTTP 404** with `Cannot GET /api/generateList.php` on 2026-11-12. The adapter raises `UnsupportedIntegration` instead of pretending to work. |
| B — `developer_api` | **Implemented, credential-gated** | Built against `https://docs.perchanceai.art` and `https://api.perchanceai.art/api/v1/developer`. Live `GET /models` returned **HTTP 200** with 47 models (19 image, 28 video). Without a token, `POST /generations/estimate` returned **401 `DEVELOPER_TOKEN_REQUIRED`**. |
| C — `manual` | **Implemented** | Writes the prompt, negative prompt, parameters and a browser handoff file. A human downloads the result and uses `import_generated.py`. |

Mode B behaviour:

- Model discovery comes from the live catalog; no model key is hardcoded.
- A chargeable request requires an estimate, a credit limit and `--confirm`.
- The idempotency record is saved before submission.
- An uncertain submission is not retried with a fresh key.
- The API key is read only from `PERCHANCEAI_API_KEY`; it is never accepted as a
  CLI flag or written to prompts, logs, manifests or signed output URLs.

**Not verified:** no charged generation and no live reference-upload run, because
no credentials were available. Those paths are implemented from the documented
API but remain unexercised end-to-end.

The unofficial community iframe/Cloudflare workaround is deliberately not
implemented or documented as supported.

---

## 7. Test and verification results

### Automated tests

```text
python -m pytest -q
98 passed, 1 warning in about 10-11s
```

The single warning is a third-party `anyio` pytest plugin deprecation
(`_pytest.python.CallSpec2` renamed to `CallSpec`, removal in pytest 10). It is
not raised by project code.

Coverage includes:

- image helpers, anchors and resampling;
- edge-connected background removal and alpha cleanup;
- frame alignment, preview formats and animation validation;
- sheet build/slice, empty cells, natural ordering, atlas packing and seam checks;
- technical QA, visual review lifecycle and manifest schema/relative paths;
- generic, Godot and Unity export, Aseprite refusal;
- prompt construction and provider registry;
- Perchance configuration and adapter behaviour with an injected transport (no
  network);
- CLI acceptance flows for the main tools.

### Build verification

- Demo pipeline: four assets `TECHNICAL_PASS`, four reviews applied, six exports.
- Manifest hash verification: `PASS`, 36 files checked, zero errors.
- All four manifests validate against `schemas/asset_manifest.schema.json`.
- Godot `.tres` and Unity `.meta`/slice files were structurally validated
  (unique sub-resource IDs, `load_steps`, rectangle bounds). They were **not**
  opened in the Godot or Unity editors.

---

## 8. Honest limitations

1. **No human approval.** All example approvals are AI-authored and scoped to
   `demo_or_internal`; `human_approved` is `false`.
2. **No charged PerchanceAI generation.** Model discovery and the missing-token
   error were verified live; generation, billing and reference upload were not.
3. **Mode A is unsupported.** The documented tutorial endpoint returned 404.
4. **Engine artifacts are not editor-verified.** Godot and Unity outputs are
   practical import templates, not proof that an engine project opens cleanly.
5. **No native Aseprite/LibreSprite writer.** The exporter refuses rather than
   emitting a fake `.aseprite` file.
6. **Demo art is procedural.** It is not AI art and is not a quality benchmark
   for any provider.
7. **Windows-first testing.** The code is platform-neutral, but the original
   suite was run on Windows/Python 3.12 only. The GitHub Actions workflow now
   covers Ubuntu and Windows on Python 3.10-3.12.
8. **Not pushed.** The workspace is prepared as a git repository for GitHub
   (license, contributing guide, security policy, issue/PR templates and CI), but
   no remote was configured and nothing was pushed.

---

## 9. Remaining tasks

- Obtain a human visual sign-off and set `human_approved: true` where justified.
- Run one authorised, budgeted developer-API generation and one reference-upload
  test with real credentials.
- Open the Godot and Unity exports in their editors and record import results.
- Add an optional native Aseprite writer only if a reliable library or format
  target is chosen; keep the honest refusal until then.
- Add CI (Linux + Windows) running `pytest` and the demo build. A workflow now
  exists at `.github/workflows/ci.yml`; watch the first run and fix any
  platform-specific failures.
- Replace procedural demo art with provider output in a separate project when
  credentials and budget exist; do not overwrite the reproducible demo.

---

## 10. Reproduce

```powershell
cd 2d-sprite-studio
python -m pip install -r requirements.txt

# Rebuild art, processing, QA, reviews, manifests and exports
python scripts/build_demo_assets.py --stage all

# Run the suite
python -m pytest -q
```

Expected: four `TECHNICAL_PASS` assets, four review records applied, six exports,
manifest hash verification `PASS`, and `98 passed` with the external `anyio`
warning.
