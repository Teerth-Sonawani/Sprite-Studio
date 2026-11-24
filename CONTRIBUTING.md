# Contributing

Thanks for taking a look at 2D Sprite Studio. The project is a file-driven
workspace for planning, generating, processing, validating and exporting 2D game
art. Contributions are welcome, but the QA and provenance rules are part of the
design, not optional extras.

## Before you start

1. Read [`AGENTS.md`](AGENTS.md) — it contains the non-negotiable operating rules.
2. Read [`docs/WORKFLOW.md`](docs/WORKFLOW.md) and the relevant guide in
   [`docs/`](docs/).
3. If you are changing an asset, read that project's brief and style guide first.

If a change conflicts with a schema, a frozen style guide or an approval rule,
stop and open an issue rather than working around it.

## Development setup

Requires Python 3.10 or newer. The project is developed and tested on 3.12.

```bash
git clone <your-fork-or-clone-url>
cd Sprite-Studio

python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -e ".[all]"
```

`.[all]` installs the optional video, SciPy and test extras. If you only need the
core pipeline, `pip install -e .` is enough.

## Running the checks

```bash
# Full test suite with the coverage gate
python -m pytest -q --cov=sprite_studio --cov-report=term-missing

# Static checks
python -m ruff check sprite_studio tools scripts tests
python -m mypy sprite_studio

# Rebuild the example project and verify every manifest hash
python scripts/build_demo_assets.py --stage all

# Byte-compile the package and command-line tools
python -m compileall -q sprite_studio tools
```

All four checks should succeed before you open a pull request. The test suite
does not make network calls and does not require provider credentials. To verify
the demo build is reproducible, run it twice with `SOURCE_DATE_EPOCH` set and
compare the two file trees; CI does this for you.

## What to change

- **Code:** put reusable logic and tool implementations in `sprite_studio/`;
  keep `tools/` as thin shims that preserve the `python tools/<name>.py` form.
- **Configuration:** prefer data edits in `config/` over new code paths.
- **Schemas:** update `schemas/` and the matching docs when a structured format
  changes. Add a test that exercises the new field.
- **Assets:** follow the naming rules in `AGENTS.md` §5. Keep sources under
  `assets/source/`, in-progress work under `assets/working/`, and reviewed work
  under `assets/approved/`.
- **Docs:** update `README.md`, `docs/` or `CHANGELOG.md` when a claim
  or limitation changes. Prefer honest limitations over optimistic marketing.

## Quality rules

These are enforced by review, not just by tests:

- Technical checks may reach `TECHNICAL_PASS`; they must never produce
  `APPROVED`.
- `APPROVED` needs a recorded visual review with evidence paths.
- `human_approved: true` requires a human reviewer. An AI review is scoped to
  `demo_or_internal`.
- Do not claim a feature works if it was not exercised. If a provider path is
  untested, say so.
- Do not hardcode model keys; discover them from the provider catalog.
- Do not retry an uncertain chargeable request with a fresh idempotency key.

## Secrets and safety

- Never commit `.env`, API keys, tokens or signed URLs.
- The only supported credential source is the environment
  (`PERCHANCEAI_API_KEY`).
- Do not add code that bypasses Cloudflare, reverse-engineers private endpoints
  or automates browser challenges.
- Chargeable generation requires an estimate, a budget and explicit confirmation.
- Report a security issue privately as described in [`SECURITY.md`](SECURITY.md).

## Art and licensing

- Do not submit protected characters, logos or an imitation of a living artist's
  signature style. Describe visual characteristics instead.
- Example art is original procedural demo art. Generated art remains subject to
  the provider's terms and the model's licence.
- By contributing, you agree that your contribution is licensed under the MIT
  License in [`LICENSE`](LICENSE).

## Pull requests

- Keep a pull request focused. Separate refactors from behaviour changes.
- Describe what changed, why, and what you actually ran.
- Include the commands and results for tests and the demo build.
- Add screenshots, contact sheets or previews for visible art changes.
- Call out limitations, follow-up work and anything you could not verify.
- Link the issue the pull request addresses, if there is one.

Use the pull-request template; it mirrors the checklist above.

## Commit messages

Short, imperative summaries are preferred, for example:

```text
Add tile seam validation report
Fix alpha cleanup for enclosed holes
Document the untested Perchance reference-upload path
```

No particular convention is enforced, but the history should stay readable.

## Code style

- Follow the existing style: four spaces, type hints where they help, small
  functions and explicit error messages.
- Keep provider calls behind the `ImageProvider` interface.
- Prefer standard library and declared dependencies; do not add a dependency for
  a small helper.
- Run `ruff`, `mypy` and `python -m pytest --cov=sprite_studio` before pushing.
  They are enforced in CI; see the commands above.

## Reporting bugs

Use the GitHub issue templates. Include:

- the command or workflow you ran;
- the expected and actual result;
- the Python version and operating system;
- relevant file paths and report JSON (redact secrets);
- whether the failure is deterministic.

For art quality issues, attach the contact sheet or preview and name the frame.
"Make it better" is not actionable; "frame 2 has a dark fringe on the left
silhouette" is.
