"""Configuration helpers for studio, providers and profiles."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent


def load_yaml(path: str | Path) -> dict:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Configuration not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected a mapping in {path}")
    return data


def load_config(name: str, root: str | Path | None = None) -> dict:
    """Load ``config/<name>.yaml`` from the workspace root.

    This is the single entry point for live configuration.  Passing ``root``
    is mainly useful for tests that need an isolated config directory.
    """

    root = Path(root) if root else ROOT
    return load_yaml(root / "config" / f"{name}.yaml")


def quality_profile(name: str, root: str | Path | None = None) -> dict:
    """Return the technical spec from ``config/quality_profiles.yaml``.

    An unknown name raises ``ValueError`` rather than silently falling back to
    no checks, because a typo in a profile name would otherwise look like a pass.
    """

    profiles = (load_config("quality_profiles", root).get("profiles") or {})
    if name not in profiles:
        raise ValueError(
            f"Unknown QA profile {name!r}; available: {sorted(profiles)}"
        )
    return dict(profiles[name].get("technical") or {})


def deep_get(data: dict, dotted: str, default=None):
    current: Any = data
    for part in dotted.split("."):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return current


def env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    return value if value not in (None, "") else default


def env_flag(name: str, default: bool = False) -> bool:
    value = env(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def redact(value: str | None, keep: int = 4) -> str:
    if not value:
        return ""
    if len(value) <= keep:
        return "*" * len(value)
    return value[:keep] + "..." + "*" * max(4, min(12, len(value) - keep))
