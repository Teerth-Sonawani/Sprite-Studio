#!/usr/bin/env python
"""Compatibility shim for the ``generate_manifest`` tool.

The implementation lives in ``sprite_studio.tools.generate_manifest`` so it is available
as an installed console entry point.  ``python tools/generate_manifest.py`` still works.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sprite_studio.cli import run  # noqa: E402
from sprite_studio.tools.generate_manifest import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(run(main))
