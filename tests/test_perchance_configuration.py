"""Perchance configuration tests: modes, safety and secret handling."""

from __future__ import annotations

import json

import pytest

from sprite_studio.providers.perchance.configuration import DEFAULT_BASE_URL, PerchanceConfig


def test_defaults_are_manual_and_safe():
    config = PerchanceConfig()
    assert config.mode == "manual"
    assert config.base_url == DEFAULT_BASE_URL
    assert config.require_approval is True
    assert config.api_key is None


def test_invalid_mode_rejected():
    with pytest.raises(ValueError):
        PerchanceConfig(mode="wishful_thinking")


def test_plain_http_is_refused_unless_explicit():
    with pytest.raises(ValueError):
        PerchanceConfig(mode="developer_api", base_url="http://localhost:8000/api")
    allowed = PerchanceConfig(
        mode="developer_api",
        base_url="http://localhost:8000/api",
        allow_insecure_http=True,
    )
    assert allowed.base_url.startswith("http://")


def test_negative_limits_rejected():
    with pytest.raises(ValueError):
        PerchanceConfig(max_credits=-1)
    with pytest.raises(ValueError):
        PerchanceConfig(poll_interval=-1)
    with pytest.raises(ValueError):
        PerchanceConfig(max_polls=0)


def test_developer_api_constructs_without_a_key_for_public_discovery():
    config = PerchanceConfig(mode="developer_api")
    assert config.mode == "developer_api"
    assert config.api_key is None


def test_public_dict_redacts_the_key():
    config = PerchanceConfig(mode="developer_api", api_key="sk-super-secret-value")
    public = config.public_dict()
    assert public["has_api_key"] is True
    assert public["api_key"] != "sk-super-secret-value"
    assert "***" in public["api_key"]
    assert "sk-super-secret-value" not in config.masked()
    assert json.loads(config.masked())["has_api_key"] is True


def test_from_env_reads_settings_without_logging_key(monkeypatch, tmp_path):
    monkeypatch.setenv("PERCHANCE_MODE", "developer_api")
    monkeypatch.setenv("PERCHANCEAI_API_KEY", "env-secret-key")
    monkeypatch.setenv("PERCHANCE_MAX_CREDITS", "12.5")
    monkeypatch.setenv("PERCHANCE_OUTPUT_DIR", str(tmp_path / "output"))
    config = PerchanceConfig.from_env()
    assert config.mode == "developer_api"
    assert config.api_key == "env-secret-key"
    assert config.max_credits == 12.5
    assert config.output_dir == tmp_path / "output"
    assert "env-secret-key" not in config.masked()
