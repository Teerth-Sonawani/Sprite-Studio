"""Provider registry and factory.

Configuration is data-driven.  Adding a provider means implementing the
ImageProvider contract and registering a factory here; the processing pipeline
does not change.
"""

from __future__ import annotations

from pathlib import Path

from sprite_studio.config import ROOT, load_yaml
from sprite_studio.errors import UsageError

from .base_provider import ImageProvider
from .mock.adapter import MockProvider
from .perchance.adapter import PerchanceProvider
from .perchance.configuration import PerchanceConfig


def _providers_config(path: str | Path | None = None) -> dict:
    if path:
        return load_yaml(path)
    return load_yaml(ROOT / "config" / "providers.yaml")


def available_providers(config_path: str | Path | None = None) -> list[str]:
    data = _providers_config(config_path)
    return sorted((data.get("providers") or {}).keys())


def create_provider(name: str, mode: str | None = None, config_path: str | Path | None = None, **kwargs) -> ImageProvider:
    config = _providers_config(config_path)
    providers = config.get("providers") or {}
    if name not in providers:
        raise UsageError(f"Unknown provider {name!r}; available: {sorted(providers)}")
    entry = providers[name]
    if entry.get("enabled") is False:
        raise UsageError(f"Provider {name!r} is disabled in config/providers.yaml")
    if name == "mock":
        output_dir = kwargs.pop("output_dir", None)
        if kwargs:
            raise UsageError(f"Unsupported mock provider options: {sorted(kwargs)}")
        return MockProvider(output_dir=output_dir) if output_dir is not None else MockProvider()
    if name == "perchance":
        chosen_mode = mode or kwargs.pop("mode", None) or entry.get("default_mode", "manual")
        perchance = PerchanceConfig.from_env(mode=chosen_mode)
        # Allow explicit overrides without leaking them into logs.  `None` means
        # "keep the environment/default value", not "overwrite with nothing".
        for key in ("api_key", "base_url", "max_credits", "require_approval", "output_dir", "timeout", "app_id"):
            if key in kwargs and kwargs[key] is not None:
                setattr(perchance, key, kwargs.pop(key))
        perchance.__post_init__()
        return PerchanceProvider(perchance, **kwargs)
    raise UsageError(f"Provider {name!r} is registered but has no factory")
