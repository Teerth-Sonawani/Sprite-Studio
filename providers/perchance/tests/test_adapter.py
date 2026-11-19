"""Adapter tests using an injected transport. No network, no real credentials."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest
from PIL import Image

from providers.base_provider import GenerationRequest, GenerationResult
from providers.perchance.adapter import PerchanceProvider
from providers.perchance.configuration import PerchanceConfig
from sprite_studio.errors import ApprovalRequired, BudgetExceeded, ProviderError, UnsupportedIntegration, UsageError

CATALOG = {
    "models": [
        {
            "model_key": "test-image",
            "display_name": "Test Image Model",
            "modality": "image",
            "operations": ["image_generation"],
            "input_schema": {"type": "object", "properties": {"seed": {"type": "integer"}}},
            "limits": {"max_n": 4},
            "price": 1,
            "price_unit": "image",
        },
        {
            "model_key": "test-video",
            "display_name": "Test Video Model",
            "modality": "video",
            "operations": ["video_generation"],
            "input_schema": {"type": "object", "properties": {}},
        },
    ]
}


def _json(data: dict, status: int = 200):
    return status, {}, json.dumps({"success": status < 400, "data": data}).encode("utf-8")


def _png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGBA", (8, 8), (255, 0, 0, 255)).save(buffer, format="PNG")
    return buffer.getvalue()


class FakeTransport:
    def __init__(self, handler):
        self.handler = handler
        self.calls: list[dict] = []

    def __call__(self, method, url, headers, body, timeout):
        self.calls.append({"method": method, "url": url, "headers": dict(headers), "body": body})
        return self.handler(method, url, dict(headers), body)


def _config(tmp_path, **overrides) -> PerchanceConfig:
    values = {
        "mode": "developer_api",
        "api_key": "secret-key",
        "base_url": "https://api.test/api/v1/developer",
        "output_dir": tmp_path / "out",
        "idempotency_store": tmp_path / "idempotency.jsonl",
        "require_approval": True,
        "max_credits": 50.0,
    }
    values.update(overrides)
    return PerchanceConfig(**values)


def _provider(tmp_path, handler, **overrides) -> tuple[PerchanceProvider, FakeTransport]:
    transport = FakeTransport(handler)
    return PerchanceProvider(_config(tmp_path, **overrides), transport=transport, sleeper=lambda _: None), transport


def _router(estimate_credits=2, generation_status: int = 200, generation_body: dict | None = None):
    def handler(method, url, headers, body):
        if method == "GET" and url.endswith("/models"):
            return _json(CATALOG)
        if method == "POST" and url.endswith("/generations/estimate"):
            return _json({"estimated_credits": estimate_credits, "model_key": "test-image", "operation": "image_generation"})
        if method == "POST" and url.endswith("/generations"):
            if generation_status >= 400:
                return generation_status, {}, json.dumps({"success": False, "code": "SERVER_ERROR", "message": "boom"}).encode()
            return _json(generation_body or {"generation_id": "gen-1", "status": "queued", "model_key": "test-image", "outputs": []})
        raise AssertionError(f"Unexpected request: {method} {url}")

    return handler


def test_list_models_is_public_and_cached(tmp_path):
    provider, transport = _provider(tmp_path, _router())
    models = provider.list_models()
    assert [model.model_key for model in models] == ["test-image", "test-video"]
    assert "Authorization" not in transport.calls[0]["headers"]
    provider.list_models()
    assert len(transport.calls) == 1


def test_model_lookup_rejects_invented_key(tmp_path):
    provider, _ = _provider(tmp_path, _router())
    with pytest.raises(ProviderError, match="not in the current catalog"):
        provider.model("invented-model")


def test_estimate_requires_api_key_before_any_network(tmp_path):
    provider, transport = _provider(tmp_path, _router(), api_key=None)
    request = GenerationRequest(prompt="a slime", model_key="test-image")
    with pytest.raises(ProviderError, match="PERCHANCEAI_API_KEY"):
        provider.estimate_cost(request)
    assert transport.calls == []


def test_generate_requires_confirmation(tmp_path):
    provider, transport = _provider(tmp_path, _router())
    request = GenerationRequest(prompt="a slime", model_key="test-image", confirmed=False)
    with pytest.raises(ApprovalRequired):
        provider.generate(request)
    assert len(transport.calls) == 1  # catalog lookup only


def test_budget_gate_blocks_submission(tmp_path):
    provider, transport = _provider(tmp_path, _router(estimate_credits=100))
    request = GenerationRequest(prompt="a slime", model_key="test-image", confirmed=True, budget_credits=5)
    with pytest.raises(BudgetExceeded):
        provider.generate(request)
    assert not any(call["url"].endswith("/generations") for call in transport.calls)


def test_unknown_parameter_rejected(tmp_path):
    provider, transport = _provider(tmp_path, _router())
    request = GenerationRequest(
        prompt="a slime",
        model_key="test-image",
        parameters={"bogus": 1},
        confirmed=True,
    )
    with pytest.raises(UsageError, match="Parameters not accepted"):
        provider.generate(request)
    assert len(transport.calls) == 1


def test_operation_must_be_supported_by_model(tmp_path):
    provider, _ = _provider(tmp_path, _router())
    request = GenerationRequest(prompt="a slime", model_key="test-video", operation="image_generation", confirmed=True)
    with pytest.raises(UsageError, match="does not support"):
        provider.generate(request)


def test_generate_success_records_provenance_and_idempotency(tmp_path):
    provider, transport = _provider(tmp_path, _router())
    request = GenerationRequest(
        prompt="A moss-covered slime, side view",
        model_key="test-image",
        parameters={"seed": 7},
        confirmed=True,
        budget_credits=10,
        metadata={"asset_id": "moss_slime", "idempotency_key": "fixed-key"},
    )
    result = provider.generate(request)
    assert result.status == "queued"
    assert result.generation_id == "gen-1"
    assert result.prompt_path and Path(result.prompt_path).is_file()
    assert result.record_path and Path(result.record_path).is_file()

    record = json.loads(Path(result.record_path).read_text(encoding="utf-8"))
    assert record["status"] == "queued"
    assert record["idempotency_key"] == "fixed-key"
    assert record["asset_id"] == "moss_slime"

    generation_calls = [call for call in transport.calls if call["url"].endswith("/generations")]
    assert len(generation_calls) == 1
    headers = generation_calls[0]["headers"]
    assert headers["Authorization"] == "Bearer secret-key"
    assert headers["Idempotency-Key"] == "fixed-key"
    body = json.loads(generation_calls[0]["body"])
    assert body["prompt"].startswith("A moss")
    assert body["parameters"] == {"seed": 7}

    prompt_text = Path(result.prompt_path).read_text(encoding="utf-8")
    assert "secret-key" not in prompt_text
    store = (tmp_path / "idempotency.jsonl").read_text(encoding="utf-8")
    assert "fixed-key" in store
    assert "secret-key" not in store


def test_uncertain_submission_saves_key_and_does_not_retry(tmp_path):
    provider, transport = _provider(tmp_path, _router(generation_status=500))
    request = GenerationRequest(
        prompt="a slime",
        model_key="test-image",
        confirmed=True,
        budget_credits=10,
        metadata={"idempotency_key": "uncertain-key", "asset_id": "slime"},
    )
    with pytest.raises(ProviderError, match="idempotency key"):
        provider.generate(request)
    generation_calls = [call for call in transport.calls if call["url"].endswith("/generations")]
    assert len(generation_calls) == 1
    record_path = tmp_path / "out" / "records" / "uncertain-key.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert record["status"] == "submission_uncertain"
    assert "uncertain-key" in (tmp_path / "idempotency.jsonl").read_text(encoding="utf-8")


def test_wait_for_generation_polls_until_terminal(tmp_path):
    states = iter(
        [
            {"generation_id": "gen-1", "status": "running"},
            {"generation_id": "gen-1", "status": "succeeded", "outputs": []},
        ]
    )
    provider, transport = _provider(tmp_path, lambda *args: _json(next(states)))
    result = provider.wait_for_generation("gen-1")
    assert result.status == "succeeded"
    assert len(transport.calls) == 2


def test_download_never_sends_bearer_to_output_host(tmp_path):
    output_url = "https://cdn.test/output.png"

    def handler(method, url, headers, body):
        assert method == "GET"
        assert url == output_url
        assert "Authorization" not in headers
        return 200, {}, _png_bytes()

    provider, _ = _provider(tmp_path, handler)
    result = GenerationResult(
        provider="perchance",
        mode="developer_api",
        status="succeeded",
        generation_id="gen-1",
        outputs=[{"url": output_url}],
    )
    saved = provider.download_result(result, tmp_path / "downloads" / "sprite.png")
    assert len(saved) == 1
    with Image.open(saved[0]) as image:
        assert image.size == (8, 8)
    assert (tmp_path / "downloads" / "sprite.download.json").is_file()


def test_download_rejects_invalid_image(tmp_path):
    provider, _ = _provider(tmp_path, lambda *args: (200, {}, b"not an image"))
    result = GenerationResult(
        provider="perchance",
        mode="developer_api",
        status="succeeded",
        generation_id="gen-1",
        outputs=[{"url": "https://cdn.test/output.png"}],
    )
    with pytest.raises(ProviderError, match="not a valid image"):
        provider.download_result(result, tmp_path / "bad.png")
    assert not (tmp_path / "bad.png").exists()


def test_reference_upload_uses_signed_host_without_bearer(tmp_path):
    image_path = tmp_path / "reference.png"
    image_path.write_bytes(_png_bytes())
    signed_url = "https://storage.test/signed-put"

    def handler(method, url, headers, body):
        if method == "POST" and url.endswith("/uploads"):
            return _json(
                {
                    "upload_id": "upload-1",
                    "upload_url": signed_url,
                    "method": "PUT",
                    "required_headers": {"X-Signed": "yes"},
                }
            )
        if method == "PUT" and url == signed_url:
            assert "Authorization" not in headers
            assert headers["X-Signed"] == "yes"
            return 200, {}, b""
        if method == "POST" and url.endswith("/uploads/upload-1/complete"):
            return _json({"upload_id": "upload-1", "status": "ready"})
        raise AssertionError(f"Unexpected request: {method} {url}")

    provider, _ = _provider(tmp_path, handler)
    result = provider.upload_reference(image_path, role="reference_image")
    assert result["upload_id"] == "upload-1"
    with pytest.raises(UsageError):
        provider.upload_reference(image_path, role="invalid-role")


def test_manual_handoff_writes_prompt_and_instructions(tmp_path):
    provider, transport = _provider(tmp_path, _router(), mode="manual", api_key=None)
    request = GenerationRequest(prompt="A moss slime", model_key="", metadata={"asset_id": "moss_slime"})
    result = provider.generate(request)
    assert result.status == "manual_required"
    assert transport.calls == []
    prompt_path = Path(result.prompt_path)
    assert prompt_path.is_file()
    assert prompt_path.read_text(encoding="utf-8").strip() == "A moss slime"
    handoff = prompt_path.with_suffix(".handoff.md")
    assert handoff.is_file()
    text = handoff.read_text(encoding="utf-8")
    assert "Paste the prompt" in text
    assert "does not automate the browser" in text


def test_documented_tutorial_mode_is_explicitly_unsupported(tmp_path):
    provider, transport = _provider(tmp_path, _router(), mode="documented_tutorial")
    with pytest.raises(UnsupportedIntegration, match="HTTP 404"):
        provider.generate(GenerationRequest(prompt="a slime", model_key="test-image"))
    assert transport.calls == []


def test_capabilities_do_not_overstate_support(tmp_path):
    provider, _ = _provider(tmp_path, _router())
    capabilities = provider.capabilities()
    assert capabilities["modes"] == ["developer_api", "manual"]
    assert capabilities["manual_handoff"] is True
    assert "unsupported" in capabilities["documented_tutorial_endpoint"]
