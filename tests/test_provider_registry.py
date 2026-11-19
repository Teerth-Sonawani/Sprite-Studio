"""Provider registry and offline mock-provider tests."""

from __future__ import annotations

import pytest
from PIL import Image

from providers.base_provider import GenerationRequest
from providers.mock.adapter import MockProvider
from providers.perchance.adapter import PerchanceProvider
from providers.provider_registry import available_providers, create_provider
from sprite_studio.errors import UsageError


def test_registry_lists_known_providers():
    providers = available_providers()
    assert "mock" in providers
    assert "perchance" in providers


def test_registry_creates_mock_provider(tmp_path):
    provider = create_provider("mock", output_dir=tmp_path / "mock")
    assert isinstance(provider, MockProvider)
    assert provider.output_dir == tmp_path / "mock"


def test_registry_creates_perchance_manual_provider(tmp_path):
    provider = create_provider("perchance", mode="manual", output_dir=tmp_path / "perchance")
    assert isinstance(provider, PerchanceProvider)
    assert provider.config.mode == "manual"
    assert provider.config.output_dir == tmp_path / "perchance"
    assert provider.config.api_key is None or provider.config.api_key


def test_registry_rejects_unknown_and_disabled(tmp_path):
    with pytest.raises(UsageError, match="Unknown provider"):
        create_provider("imaginary")
    config = tmp_path / "providers.yaml"
    config.write_text(
        "providers:\n  mock:\n    enabled: false\n    type: offline\n",
        encoding="utf-8",
    )
    with pytest.raises(UsageError, match="disabled"):
        create_provider("mock", config_path=config)


def test_mock_provider_is_deterministic_and_local(tmp_path):
    provider = MockProvider(output_dir=tmp_path / "out")
    request = GenerationRequest(
        prompt="geometric test shape",
        model_key="mock-shape-v1",
        parameters={"seed": 42, "width": 64, "height": 64},
    )
    first = provider.generate(request)
    second = provider.generate(request)
    assert first.status == "succeeded"
    assert first.generation_id == second.generation_id == "mock-42"
    first_path = tmp_path / "out" / "mock_42_64x64.png"
    assert first_path.is_file()
    with Image.open(first_path) as image:
        assert image.size == (64, 64)
        assert image.mode == "RGBA"
    assert first.estimated_credits == 0
    assert provider.capabilities()["modes"] == ["offline"]


def test_mock_provider_validates_dimensions_and_prompt(tmp_path):
    provider = MockProvider(output_dir=tmp_path / "out")
    with pytest.raises(UsageError):
        provider.generate(GenerationRequest(prompt="", model_key="mock-shape-v1"))
    with pytest.raises(UsageError):
        provider.generate(
            GenerationRequest(prompt="x", model_key="mock-shape-v1", parameters={"width": 4, "height": 4})
        )


def test_mock_provider_health_and_download(tmp_path):
    provider = MockProvider(output_dir=tmp_path / "out")
    health = provider.health_check()
    assert health.ok is True
    assert health.credits == 0
    result = provider.generate(
        GenerationRequest(prompt="shape", model_key="mock-shape-v1", parameters={"seed": 3, "width": 16, "height": 16})
    )
    saved = provider.download_result(result, tmp_path / "download.png")
    assert saved and saved[0].is_file()
    assert provider.get_status("mock-3").status == "succeeded"
