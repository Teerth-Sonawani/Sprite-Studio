"""Perchance integration configuration.

Three modes are intentionally distinct:

manual
    Prepare a prompt and send the user to the browser.  Always available.
developer_api
    The documented PerchanceAI developer API at api.perchanceai.art.  Requires a
    formal account key and is the only mode this workspace bills automatically.
documented_tutorial
    The interface described by https://perchance.org/api-tutorial.  Investigation
    found its only endpoint returns HTTP 404, so the adapter reports it as
    unsupported instead of inventing behaviour.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sprite_studio.config import env, env_flag, redact

DEFAULT_BASE_URL = "https://api.perchanceai.art/api/v1/developer"
DEFAULT_GENERATOR_URL = "https://perchance.org/ai-text-to-image-generator"
SUPPORTED_MODES = {"manual", "developer_api", "documented_tutorial"}


@dataclass
class PerchanceConfig:
    mode: str = "manual"
    api_key: str | None = field(default=None, repr=False)
    base_url: str = DEFAULT_BASE_URL
    generator_url: str = DEFAULT_GENERATOR_URL
    app_id: str = "perchanceai"
    model_key: str | None = None
    max_credits: float = 50.0
    require_approval: bool = True
    timeout: float = 60.0
    poll_interval: float = 2.0
    max_polls: int = 150
    output_dir: Path = Path("generations")
    idempotency_store: Path = Path("generations/idempotency.jsonl")
    request_timeout: float = 60.0
    allow_insecure_http: bool = False
    extra: dict = field(default_factory=dict)

    def __post_init__(self):
        self.mode = (self.mode or "manual").strip().lower()
        if self.mode not in SUPPORTED_MODES:
            raise ValueError(f"PERCHANCE_MODE must be one of {sorted(SUPPORTED_MODES)}")
        if self.mode == "developer_api" and not self.api_key:
            # Do not fail at construction: health_check/list_models are public and
            # useful for setup diagnostics.  Chargeable calls enforce the key.
            pass
        if self.max_credits < 0:
            raise ValueError("max_credits cannot be negative")
        if self.poll_interval < 0 or self.max_polls < 1:
            raise ValueError("Invalid polling configuration")
        if self.base_url.startswith("http://") and not self.allow_insecure_http:
            raise ValueError("Refusing plain HTTP for the developer API; use HTTPS or allow_insecure_http for local tests")
        self.output_dir = Path(self.output_dir)
        self.idempotency_store = Path(self.idempotency_store)

    @classmethod
    def from_env(cls, **overrides) -> "PerchanceConfig":
        values: dict[str, Any] = {
            "mode": env("PERCHANCE_MODE", "manual"),
            "api_key": env("PERCHANCEAI_API_KEY"),
            "base_url": env("PERCHANCEAI_API_BASE_URL", DEFAULT_BASE_URL),
            "generator_url": env("PERCHANCE_GENERATOR_URL", DEFAULT_GENERATOR_URL),
            "app_id": env("PERCHANCEAI_APP_ID", "perchanceai"),
            "model_key": env("PERCHANCE_MODEL_KEY"),
            "max_credits": float(env("PERCHANCE_MAX_CREDITS", "50") or 50),
            "require_approval": env_flag("PERCHANCE_REQUIRE_APPROVAL", True),
            "timeout": float(env("PERCHANCE_TIMEOUT", "60") or 60),
            "poll_interval": float(env("PERCHANCE_POLL_INTERVAL", "2") or 2),
            "max_polls": int(env("PERCHANCE_MAX_POLLS", "150") or 150),
            "output_dir": env("PERCHANCE_OUTPUT_DIR", "generations"),
            "idempotency_store": env("PERCHANCE_IDEMPOTENCY_STORE", "generations/idempotency.jsonl"),
        }
        values.update({k: v for k, v in overrides.items() if v is not None})
        return cls(**values)

    def public_dict(self) -> dict:
        return {
            "mode": self.mode,
            "base_url": self.base_url,
            "generator_url": self.generator_url,
            "app_id": self.app_id,
            "model_key": self.model_key,
            "max_credits": self.max_credits,
            "require_approval": self.require_approval,
            "timeout": self.timeout,
            "poll_interval": self.poll_interval,
            "max_polls": self.max_polls,
            "api_key": redact(self.api_key) if self.api_key else None,
            "has_api_key": bool(self.api_key),
            "output_dir": str(self.output_dir),
        }

    def masked(self) -> str:
        import json

        return json.dumps(self.public_dict(), indent=2)
