# Perchance Integration

Investigation date: **2026-11-12**. This document records what was actually
tested, not what an integration might ideally do.

## 1. Summary

| Interface | Status in this workspace | Notes |
|---|---|---|
| `https://perchance.org/api-tutorial` | **Not usable as documented** | The page describes a text-generator API; its only endpoint returned **HTTP 404** when tested. |
| PerchanceAI developer API (`https://api.perchanceai.art`) | **Implemented, credential-gated** | Documented at `https://docs.perchanceai.art`; public model discovery verified live. |
| Manual Perchance handoff | **Implemented, always available** | Prepare prompt, user generates in browser, import result. |
| Unofficial community iframe "Image API" | **Not implemented** | Not treated as an official integration; see §7. |

Perchance (the generator platform) and PerchanceAI (the developer API service)
must not be assumed to share an interface, credentials or pricing. The workspace
treats them as separate.

## 2. What the supplied tutorial actually says

The rendered page at `https://perchance.org/api-tutorial` is titled "Connecting
Perchance Generator with an App using API". It explains how to call a text
generator and gives this endpoint:

```text
https://perchance.org/api/generateList.php?generator=GENERATOR_NAME&count=NUMBER_OF_RESULTS
```

It also discusses CORS proxies and browser warm-up. It does **not** document image
generation, model discovery, authentication, credits, asynchronous tasks or
reference uploads.

### Test performed

A same-origin `fetch` from the loaded tutorial page produced:

```text
GET /api/generateList.php?generator=example-generator&count=1
HTTP 404
Cannot GET /api/generateList.php
```

The endpoint does not exist at the time of testing. Therefore Mode A is **not
implemented as a working integration**. The adapter raises an explicit
`UnsupportedIntegration` error for `PERCHANCE_MODE=documented_tutorial` instead of
pretending to submit a request. No CORS proxy, anti-bot bypass or private endpoint
was used.

## 3. PerchanceAI developer API

Official documentation: `https://docs.perchanceai.art`

Agent-readable index: `https://docs.perchanceai.art/agent-docs/llms.txt`

Base URL used by the adapter:

```text
https://api.perchanceai.art/api/v1/developer
```

### Authentication

- Protected calls require `Authorization: Bearer <pca_live_...>` or a delegated
  OAuth token.
- Model discovery is public.
- Anonymous tokens cannot call business endpoints.
- The key is read from `PERCHANCEAI_API_KEY`; it is never accepted as a CLI flag,
  never written to prompts/logs, and never sent to signed output URLs.
- Create a key in the PerchanceAI account UI under Settings → API & MCP. The
  secret is shown once.

### Endpoints used

| Operation | Method/path | Auth |
|---|---|---|
| List models | `GET /models` | public |
| Account credits | `GET /credits` | key |
| Estimate credits | `POST /generations/estimate` | key |
| Create generation | `POST /generations` | key + `Idempotency-Key` |
| Get task status | `GET /generations/{id}` | key |
| Cancel task | `POST /generations/{id}/cancel` | key |
| Prepare reference upload | `POST /uploads` | key + `Idempotency-Key` |
| Complete upload | `POST /uploads/{id}/complete` | key + `Idempotency-Key` |

### Request shape

```json
{
  "model_key": "<exact key from /models>",
  "operation": "image_generation",
  "prompt": "…",
  "negative_prompt": "…",
  "parameters": {},
  "reference_upload_ids": []
}
```

Only parameters present in the selected model's `input_schema` are accepted. The
adapter validates this before submitting. Model keys, availability, limits and
prices are discovered dynamically; nothing is hardcoded.

### Response shape

Create returns `202` with a durable `generation_id`, `status`, credit fields and
`outputs` (empty until complete). Poll until `succeeded`, `failed` or `cancelled`.
An accepted request is not completion.

### Credit safety

1. `estimate` before `create`.
2. Refuse if the estimate exceeds `--budget-credits` or `PERCHANCE_MAX_CREDITS`.
3. Require `--confirm` for chargeable requests when approval is enabled.
4. Persist the prompt, estimate and idempotency key **before** submitting.
5. On an uncertain POST, do **not** retry with a new key. The key and payload are
   saved; a human must check status and retry deliberately with the same key if
   appropriate.
6. Never place a bearer token in a URL.

### Live checks performed (no charge)

| Check | Result |
|---|---|
| `GET /models` | `200`; 47 models (19 image, 28 video) at test time |
| `POST /generations/estimate` with no token | `401 DEVELOPER_TOKEN_REQUIRED` |
| Tutorial `GET /api/generateList.php` | `404` |
| Charged image generation | **Not run**; no credentials were provided |

Model counts and prices are dynamic. Re-run `models` before relying on any key.

## 4. Modes supported by the adapter

### Mode A — documented tutorial

```env
PERCHANCE_MODE=documented_tutorial
```

Result: explicit unsupported error with the 404 evidence. This is deliberate.

### Mode B — developer API

```env
PERCHANCE_MODE=developer_api
PERCHANCEAI_API_KEY=pca_live_...
PERCHANCE_MAX_CREDITS=50
PERCHANCE_REQUIRE_APPROVAL=true
```

Commands:

```powershell
python tools/generate_asset.py health --provider perchance --mode developer_api
python tools/generate_asset.py models --provider perchance --mode developer_api --modality image
python tools/generate_asset.py estimate --provider perchance --mode developer_api `
  --model "<exact model_key from models>" --prompt-file prompt.txt --budget-credits 20
# Review the printed estimate and the exact model key before continuing.
python tools/generate_asset.py generate --provider perchance --mode developer_api `
  --model "<exact model_key from models>" --prompt-file prompt.txt `
  --budget-credits 20 --confirm --wait
python tools/generate_asset.py download --provider perchance --mode developer_api `
  --result projects/example-project/manifests/generations/perchance_<timestamp>.json `
  --dest assets/source/perchance
```

`generate` does not accept `--estimate`; run the `estimate` subcommand first.
Model keys are discovered at runtime; the placeholder above is intentional.

### Mode C — manual handoff

```env
PERCHANCE_MODE=manual
```

```powershell
python tools/build_prompt.py assets/briefs/moss_slime.yaml `
  --style projects/example-project/style_guide.yaml `
  --output assets/source/prompts/moss_slime_idle.prompt.txt
python tools/generate_asset.py generate --provider perchance --mode manual `
  --brief assets/briefs/moss_slime.yaml `
  --style projects/example-project/style_guide.yaml `
  --asset-id moss_slime
```

This writes:

- `*.prompt.txt` — the prompt;
- `*.prompt.json` — metadata without credentials;
- `*.handoff.md` — instructions with the generator URL.

Then:

1. Open `https://perchance.org/ai-text-to-image-generator` (or the configured URL).
2. Paste the prompt.
3. Generate and download the image.
4. Import it:

```powershell
python tools/import_generated.py downloaded.png `
  --dest assets/source --asset-id moss_slime `
  --provider perchance --mode manual `
  --model "label shown by the interface, if any" `
  --prompt-file assets/source/prompts/moss_slime_idle.prompt.txt
```

5. Inspect, remove the background, clean alpha, validate.

Manual mode does not automate the browser, bypass Cloudflare, or scrape private
endpoints.

## 5. Prompt construction

`tools/build_prompt.py` and `tools/generate_asset.py --brief` assemble sections:

```text
SUBJECT
ART DIRECTION
COMPOSITION
CAMERA
VISUAL CHARACTERISTICS
BACKGROUND
GAME ASSET REQUIREMENTS
OUTPUT
NEGATIVE CONSTRAINTS
```

The prompt explicitly asks for one asset, a clean silhouette, no text/watermark,
and no baked checkerboard. It also warns that exact dimensions and transparency
must be verified. It does not assume the provider obeys any of this.

## 6. Candidate selection and cost control

- Default candidates: 3 (`config/studio.yaml`).
- Maximum per asset: 6.
- Every additional candidate needs a reason.
- Preserve rejected candidates under `assets/rejected/` when useful.
- Do not regenerate an approved asset without a documented reason.
- Correct local defects before generating a replacement.
- Keep the generation record: provider, mode, model key, prompt, parameters,
  generation id, source hash and output paths.

## 7. Why the unofficial community iframe API is not implemented

A community page at `perchance.org/perchance-ai-api` describes an iframe +
`postMessage` pattern, browser "warm-up" for Cloudflare, and a `removeBackground`
parameter. It is not the supplied tutorial and not the documented PerchanceAI
developer API. Depending on it would mean:

- relying on an undocumented/third-party page contract;
- requiring a browser and Cloudflare challenge passage;
- accepting unclear rate limits and terms;
- embedding an automation path this workspace cannot verify as permitted.

The workspace therefore does not ship an adapter for it. Manual handoff remains
supported, and the developer API is the supported programmatic path.

## 8. Limitations

- No charged generation was performed during the build; no credential was
  available. Live behavior beyond model discovery and the 401 check is unverified.
- Output image dimensions/transparency are provider-dependent; always inspect.
- The API's exact model catalog and pricing change; discover them at runtime.
- Reference upload + conditioning is implemented per docs but was not exercised
  against a live account.
- A successful API response proves a task completed, not that the asset is good.
- Manual mode cannot guarantee the user selected the intended model or settings;
  record what the interface actually showed.

## 9. Setup checklist

- [ ] `python tools/generate_asset.py health --provider perchance --mode developer_api`
- [ ] `python tools/generate_asset.py models --provider perchance --mode developer_api --modality image`
- [ ] Choose an exact `model_key` from that output.
- [ ] Set `PERCHANCEAI_API_KEY` in your environment (not in a tracked file).
- [ ] Set a sensible `PERCHANCE_MAX_CREDITS`.
- [ ] Run `estimate` and review the cost.
- [ ] Use `--confirm` only after approval.
- [ ] Download outputs to `assets/source/`.
- [ ] Record provenance and run the processing/QA pipeline.
