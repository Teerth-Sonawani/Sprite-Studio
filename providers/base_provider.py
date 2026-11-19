"""Provider-neutral interfaces.

The abstraction describes capabilities, not fictional endpoints.  A provider
that cannot do something reports it through `capabilities()` and raises
`UnsupportedIntegration` rather than pretending to succeed.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ModelInfo:
    model_key: str
    display_name: str
    modality: str
    operations: list[str]
    input_schema: dict = field(default_factory=dict)
    limits: dict = field(default_factory=dict)
    price: float | None = None
    price_unit: str | None = None
    description: str | None = None
    raw: dict = field(default_factory=dict)

    def supports(self, operation: str) -> bool:
        return operation in self.operations

    @classmethod
    def from_api(cls, data: dict) -> "ModelInfo":
        return cls(
            model_key=data.get("model_key", ""),
            display_name=data.get("display_name", data.get("model_key", "")),
            modality=data.get("modality", ""),
            operations=list(data.get("operations") or []),
            input_schema=data.get("input_schema") or {},
            limits=data.get("limits") or {},
            price=data.get("price"),
            price_unit=data.get("price_unit"),
            description=data.get("description"),
            raw=data,
        )


@dataclass
class GenerationRequest:
    prompt: str
    model_key: str = ""
    operation: str = "image_generation"
    negative_prompt: str = ""
    parameters: dict = field(default_factory=dict)
    reference_upload_ids: list[str] = field(default_factory=list)
    client_trace_id: str = ""
    metadata: dict = field(default_factory=dict)
    budget_credits: float | None = None
    confirmed: bool = False

    def payload(self) -> dict:
        payload: dict[str, Any] = {
            "model_key": self.model_key,
            "operation": self.operation,
            "prompt": self.prompt,
        }
        if self.negative_prompt:
            payload["negative_prompt"] = self.negative_prompt
        if self.parameters:
            payload["parameters"] = self.parameters
        if self.reference_upload_ids:
            payload["reference_upload_ids"] = self.reference_upload_ids
        if self.client_trace_id:
            payload["client_trace_id"] = self.client_trace_id
        return payload

    def validate(self) -> list[str]:
        errors = []
        if not self.prompt or not self.prompt.strip():
            errors.append("prompt is required")
        if len(self.prompt) > 8000:
            errors.append("prompt exceeds 8000 characters")
        if self.negative_prompt and len(self.negative_prompt) > 8000:
            errors.append("negative_prompt exceeds 8000 characters")
        if not self.operation:
            errors.append("operation is required")
        if self.reference_upload_ids and len(self.reference_upload_ids) > 8:
            errors.append("at most 8 reference uploads are supported")
        if self.budget_credits is not None and self.budget_credits < 0:
            errors.append("budget_credits cannot be negative")
        return errors


@dataclass
class GenerationResult:
    provider: str
    mode: str
    status: str
    generation_id: str | None = None
    model_key: str | None = None
    outputs: list[dict] = field(default_factory=list)
    estimated_credits: float | None = None
    reserved_credits: float | None = None
    charged_credits: float | None = None
    error: dict | None = None
    raw: dict = field(default_factory=dict)
    prompt_path: str | None = None
    record_path: str | None = None
    note: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_api(cls, provider: str, mode: str, data: dict) -> "GenerationResult":
        return cls(
            provider=provider,
            mode=mode,
            status=data.get("status", "unknown"),
            generation_id=data.get("generation_id"),
            model_key=data.get("model_key"),
            outputs=list(data.get("outputs") or []),
            estimated_credits=data.get("estimated_credits"),
            reserved_credits=data.get("reserved_credits"),
            charged_credits=data.get("charged_credits"),
            error=data.get("error"),
            raw=data,
        )


@dataclass
class ProviderHealth:
    ok: bool
    provider: str
    mode: str
    detail: str
    models_available: int | None = None
    credits: float | None = None
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


class ImageProvider(ABC):
    """Minimal contract implemented by real providers.

    Not every provider supports every operation.  Check `capabilities()` first.
    """

    provider_id = "base"

    @abstractmethod
    def health_check(self) -> ProviderHealth:
        ...

    @abstractmethod
    def list_models(self) -> list[ModelInfo]:
        ...

    @abstractmethod
    def estimate_cost(self, request: GenerationRequest) -> dict:
        ...

    @abstractmethod
    def generate(self, request: GenerationRequest) -> GenerationResult:
        ...

    @abstractmethod
    def get_status(self, generation_id: str) -> GenerationResult:
        ...

    @abstractmethod
    def download_result(self, result: GenerationResult, destination: str | Path) -> list[Path]:
        ...

    def capabilities(self) -> dict:
        return {
            "provider": self.provider_id,
            "list_models": True,
            "estimate_cost": True,
            "generate": True,
            "get_status": True,
            "download_result": True,
            "async": True,
            "reference_images": False,
            "transparent_background": "prompt-only",
            "manual_handoff": False,
        }


class ManualHandoffMixin:
    """For providers where generation is performed by a human in a browser."""

    def manual_handoff(self, prompt: str, destination: str | Path) -> Path:  # pragma: no cover - interface
        raise NotImplementedError
