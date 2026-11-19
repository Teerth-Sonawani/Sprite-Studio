## Summary

What changed, and why?

## Scope

- [ ] Bug fix
- [ ] New feature
- [ ] Refactor
- [ ] Documentation
- [ ] Example asset or project data
- [ ] CI / repository tooling

## Verification

List the commands you actually ran and their results.

```text
python -m pytest -q
python scripts/build_demo_assets.py --stage all
python -m compileall -q sprite_studio providers tools
```

- [ ] Tests pass.
- [ ] The example pipeline builds and verifies its manifest hashes.
- [ ] I added or updated tests for behaviour changes.
- [ ] I updated the README, docs, CHANGELOG or BUILD_REPORT where claims changed.

## Asset and QA changes

Skip this section if the pull request does not touch art or QA.

- [ ] Sources are preserved under `assets/source/`.
- [ ] Final frames share a canvas and pivot.
- [ ] Technical QA passed.
- [ ] Visual review evidence is attached.
- [ ] `human_approved` reflects a human reviewer, not an AI review.
- [ ] The manifest validates and every hash is current.

## Honesty check

- [ ] I did not claim a provider path works if I did not exercise it.
- [ ] I did not put credentials, tokens or signed URLs in tracked files.
- [ ] I listed known limitations and follow-up work.
- [ ] I did not add a protected character, logo or imitation of a living artist.

## Screenshots or previews

Attach contact sheets, GIFs or engine screenshots for visible changes.

## Related issues

Closes #
