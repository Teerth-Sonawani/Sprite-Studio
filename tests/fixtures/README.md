# Test fixtures

The suite builds its images and mini-projects at runtime in pytest's `tmp_path`
(see `tests/conftest.py`), so no binary fixtures are checked in.

This folder is reserved for small, licence-clean static fixtures if a future
test needs a real file that cannot be generated deterministically. Do not add
third-party art here without recording its licence in `LICENSE`.
