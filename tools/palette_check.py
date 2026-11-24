#!/usr/bin/env python
"""Compatibility shim for the ``palette_check`` tool.

The implementation lives in ``sprite_studio.tools.palette_check`` so it is available
as an installed console entry point.  ``python tools/palette_check.py`` still works.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sprite_studio.cli import run  # noqa: E402
from sprite_studio.tools.palette_check import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(run(main))
