#!/usr/bin/env python
"""Compatibility shim for the ``qa_review`` tool.

The implementation lives in ``sprite_studio.tools.qa_review`` so it is available
as an installed console entry point.  ``python tools/qa_review.py`` still works.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sprite_studio.cli import run  # noqa: E402
from sprite_studio.tools.qa_review import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(run(main))
