"""Timestamps for generated artefacts.

Every report, manifest and export embeds a timestamp.  Wall-clock time makes
those files change on every rebuild, which defeats reproducibility checks and
dirties the working tree for no reason.

Set ``SOURCE_DATE_EPOCH`` (seconds since the Unix epoch, the usual convention
for reproducible builds) to pin the value.  When it is unset the current time is
used, which is what a human-facing build wants.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

ENV_VAR = "SOURCE_DATE_EPOCH"


def utcnow() -> str:
    """Return an ISO-8601 UTC timestamp, honouring ``SOURCE_DATE_EPOCH``."""

    raw = os.environ.get(ENV_VAR)
    if raw is None or raw.strip() == "":
        return datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        epoch = int(raw.strip())
    except ValueError as exc:
        raise ValueError(f"{ENV_VAR} must be an integer number of seconds, got {raw!r}") from exc
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat(timespec="seconds")
