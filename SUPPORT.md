# Support

## Documentation first

- [`README.md`](README.md) — overview, installation and quick start.
- [`AGENTS.md`](AGENTS.md) — mandatory operating rules for agents and humans.
- [`docs/WORKFLOW.md`](docs/WORKFLOW.md) — the phase-by-phase pipeline.
- [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md) — common failures.
- [`projects/example-project/README.md`](projects/example-project/README.md) —
  a complete worked example with commands and evidence paths.

## Questions and bugs

- Use **GitHub Discussions** for usage questions, ideas and show-and-tell, if the
  repository has Discussions enabled.
- Use the **bug report** issue template for reproducible defects.
- Use the **feature request** template for scoped proposals.
- Use the private process in [`SECURITY.md`](SECURITY.md) for vulnerabilities.

Please include the command you ran, the Python version, your operating system,
and the relevant report or manifest paths. Redact API keys and personal data.

## What is not supported

- Bypassing Cloudflare or automating a provider's browser challenge.
- Imitating a protected character, logo or a living artist's signature style.
- Claims of human approval without a recorded human review.
- Native `.aseprite` writing. The exporter refuses rather than producing a fake
  file.

## Provider support

The provider layer has three Perchance modes and one offline mock provider. Model
discovery is live; a charged generation and reference upload were **not**
exercised in the original build because no credentials were available. Check
[`docs/PERCHANCE_INTEGRATION.md`](docs/PERCHANCE_INTEGRATION.md) before relying on
those paths in production.
