---
name: sprite-generation
description: Choose a provider, build a prompt, estimate cost, generate candidates safely and record complete provenance for 2D sprite assets.
---

# Sprite Generation

## Purpose

Produce source candidates without losing control of cost, credentials,
provenance or the difference between "generated" and "approved".

## Use when

- A new source image is needed from a provider.
- A manual Perchance handoff is being prepared.
- A generation must be retried, diagnosed or audited.
- A mock/offline dry run is needed.

## Inputs

- Validated asset brief
- Frozen style guide
- `config/providers.yaml`
- `config/studio.yaml` generation limits
- `docs/PERCHANCE_INTEGRATION.md`
- Provider health and model catalog

## Provider decision

| Situation | Use |
|---|---|
| Pipeline test, no network, deterministic fixture | `mock` provider |
| No API key, human can use the browser | Perchance `manual` |
| Formal PerchanceAI key and charge approval | Perchance `developer_api` |
| `perchance.org/api-tutorial` | **Do not use**; its endpoint returned HTTP 404 on 2026-11-12 |

Do not implement or rely on the unofficial community iframe/browser warm-up API.
It is not the supplied tutorial and not the documented developer API.

## Procedure

### 1. Build the prompt

```powershell
python tools/build_prompt.py projects/example-project/assets/briefs/moss_slime.yaml `
  --style projects/example-project/style_guide.yaml `
  --output projects/example-project/assets/source/prompts/moss_slime_idle.prompt.txt `
  --negative-output projects/example-project/assets/source/prompts/moss_slime_idle.negative.txt
```

The prompt encodes subject, art direction, composition, camera, colour, outline,
lighting, background, output and negative constraints. It does not guarantee that
the provider obeys them.

### 2. Check the provider

```powershell
python tools/generate_asset.py health --provider perchance --mode developer_api
python tools/generate_asset.py models --provider perchance --mode developer_api --modality image
```

- Use only an exact model key from the current catalog. Never hardcode or guess.
- Check `input_schema` before passing model parameters.
- Public model discovery does not need a key; chargeable calls do.

### 3. Estimate before charging

```powershell
python tools/generate_asset.py estimate --provider perchance --mode developer_api `
  --model "<exact-key>" `
  --prompt-file projects/example-project/assets/source/prompts/moss_slime_idle.prompt.txt `
  --budget-credits 20
```

`generate` does **not** accept `--estimate`. Review the printed estimate first.

### 4. Generate deliberately

```powershell
python tools/generate_asset.py generate --provider perchance --mode developer_api `
  --model "<exact-key>" `
  --prompt-file projects/example-project/assets/source/prompts/moss_slime_idle.prompt.txt `
  --budget-credits 20 --confirm --wait `
  --result-out projects/example-project/manifests/generations/moss_slime_idle.json
```

- `--confirm` is required for chargeable requests when approval is enabled.
- Default candidate count is 3; every extra candidate needs a reason.
- Preserve every source under `assets/source/`.
- Keep rejected candidates under `assets/rejected/` when useful.

### 5. Manual handoff (Mode C)

```powershell
python tools/generate_asset.py generate --provider perchance --mode manual `
  --brief projects/example-project/assets/briefs/moss_slime.yaml `
  --style projects/example-project/style_guide.yaml `
  --asset-id moss_slime
```

This writes a prompt, a prompt sidecar and a `.handoff.md` with the generator URL.
A human generates in the browser and downloads the image. Then:

```powershell
python tools/import_generated.py downloaded.png `
  --dest projects/example-project/assets/source `
  --asset-id moss_slime --provider perchance --mode manual `
  --model "label shown by the interface, if any" `
  --prompt-file projects/example-project/assets/source/prompts/moss_slime.prompt.txt
```

`import_generated.py` copies the file, hashes it and writes a provenance sidecar.
Then inspect, remove the background, clean alpha and validate.

### 6. Download developer-API outputs

```powershell
python tools/generate_asset.py download --provider perchance --mode developer_api `
  --result projects/example-project/manifests/generations/<result>.json `
  --dest projects/example-project/assets/source/perchance
```

The adapter validates that each downloaded file is an image and writes a download
record with hashes.

## Credential and cost safety

- Set `PERCHANCEAI_API_KEY` in the environment. Never pass it as a CLI flag.
- Never put the key in a prompt, URL, manifest, screenshot or log.
- Estimate, then enforce `--budget-credits` or `PERCHANCE_MAX_CREDITS`.
- Persist the prompt, estimate and idempotency key before submitting.
- On an uncertain POST, stop. Do not retry blindly with a new key. Check status
  and have a human decide.
- Never send the bearer token to a signed output URL.

## Output

- Source candidate images under `assets/source/`
- Prompt and negative prompt files
- Prompt sidecar JSON
- Generation result JSON (provider, mode, model key, id, credits, outputs)
- Provenance record with hashes

## Handoff

Send the chosen source path, prompt file, provider/mode/model and generation id to
`image-processing`. Send rejected candidates and reasons to
`quality-assurance` if selection was contested.

## Quality gate

- [ ] Prompt derives from the brief and style guide.
- [ ] Model key came from the live catalog.
- [ ] Parameters match the model's `input_schema`.
- [ ] Estimate was reviewed; budget is recorded.
- [ ] `--confirm` was used only with approval.
- [ ] Source files and provenance are preserved.
- [ ] No credentials appear in any artifact.

## Pitfalls

- Treating a `202 Accepted` as a completed image.
- Assuming a provider honoured transparency, dimensions or style.
- Regenerating before diagnosing the actual defect.
- Using a model key copied from an old blog post.
- Retrying an uncertain charge with a fresh idempotency key.
