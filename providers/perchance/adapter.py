"""Perchance provider adapter.

Mode B (developer_api) talks only to the documented PerchanceAI developer API:
https://api.perchanceai.art/api/v1/developer

Mode C (manual) prepares a prompt and a browser handoff.  Mode A is represented
only as an explicit unsupported state because the interface described by
https://perchance.org/api-tutorial was tested and its endpoint returned HTTP 404.

No private endpoints are reverse-engineered, no Cloudflare challenge is bypassed,
and no credential is ever placed in a prompt, URL or log.
"""

from __future__ import annotations

import hashlib
import json
import mimetypes
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from PIL import Image

from providers.base_provider import GenerationRequest, GenerationResult, ImageProvider, ModelInfo, ProviderHealth
from providers.perchance.configuration import PerchanceConfig
from sprite_studio.errors import ApprovalRequired, BudgetExceeded, ProviderError, UnsupportedIntegration, UsageError
from sprite_studio.image_utils import sha256_file, write_json

Transport = Callable[[str, str, dict, bytes | None, float], tuple[int, dict, bytes]]


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _default_transport(method: str, url: str, headers: dict, body: bytes | None, timeout: float) -> tuple[int, dict, bytes]:
    request = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.status, dict(response.headers), response.read()
    except HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read()
    except URLError as exc:
        raise ProviderError(f"Network error contacting PerchanceAI: {exc.reason}") from exc


class PerchanceProvider(ImageProvider):
    provider_id = "perchance"

    def __init__(self, config: PerchanceConfig | None = None, transport: Transport | None = None, sleeper: Callable[[float], None] = time.sleep):
        self.config = config or PerchanceConfig.from_env()
        self._transport = transport or _default_transport
        self._sleep = sleeper
        self._models_cache: list[ModelInfo] | None = None

    # ------------------------------------------------------------------ HTTP
    def _headers(self, auth: bool = True, idempotency_key: str | None = None) -> dict:
        headers = {
            "Accept": "application/json",
            "X-App-Id": self.config.app_id,
            "X-Request-Id": f"studio-{uuid.uuid4().hex[:12]}",
            "User-Agent": "2d-sprite-studio/1.0",
        }
        if auth:
            if not self.config.api_key:
                raise ProviderError(
                    "PERCHANCEAI_API_KEY is required for this operation. Public model discovery does not need it."
                )
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        return headers

    def _request(
        self,
        method: str,
        path: str,
        *,
        payload: dict | None = None,
        auth: bool = True,
        idempotency_key: str | None = None,
        absolute_url: str | None = None,
        extra_headers: dict | None = None,
        raw_body: bytes | None = None,
    ) -> dict:
        url = absolute_url or (self.config.base_url.rstrip("/") + path)
        headers = self._headers(auth=auth, idempotency_key=idempotency_key)
        body = raw_body
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if extra_headers:
            headers.update(extra_headers)
        status, response_headers, response_body = self._transport(method, url, headers, body, self.config.request_timeout)
        text = response_body.decode("utf-8", errors="replace")
        try:
            data = json.loads(text) if text.strip() else {}
        except json.JSONDecodeError:
            data = {"raw": text[:1000]}
        if status >= 400:
            message = data.get("message") or data.get("code") or f"HTTP {status}"
            code = data.get("code", f"HTTP_{status}")
            raise ProviderError(f"PerchanceAI {code}: {message}")
        if not data.get("success", True):
            raise ProviderError(f"PerchanceAI error: {data.get('code')} {data.get('message', '')}".strip())
        return data.get("data", data)

    # --------------------------------------------------------------- provider
    def health_check(self) -> ProviderHealth:
        errors: list[str] = []
        models = []
        credits = None
        try:
            models = self.list_models(force=True)
        except Exception as exc:
            errors.append(f"catalog: {exc}")
        if self.config.api_key:
            try:
                credits_data = self._request("GET", "/credits")
                credits = credits_data.get("balance_credits") or credits_data.get("available_credits")
            except Exception as exc:
                errors.append(f"credits: {exc}")
        else:
            errors.append("PERCHANCEAI_API_KEY is not set; chargeable calls are disabled")
        ok = bool(models) and (credits is not None or not self.config.api_key)
        detail = (
            f"{len(models)} public model(s) discovered."
            if models
            else "Public model catalog could not be reached."
        )
        if credits is not None:
            detail += f" Account credits: {credits}."
        return ProviderHealth(
            ok=ok,
            provider=self.provider_id,
            mode=self.config.mode,
            detail=detail,
            models_available=len(models) if models else None,
            credits=credits,
            errors=errors,
        )

    def list_models(self, force: bool = False) -> list[ModelInfo]:
        if self._models_cache is not None and not force:
            return list(self._models_cache)
        data = self._request("GET", "/models", auth=False)
        models = [ModelInfo.from_api(item) for item in data.get("models", [])]
        self._models_cache = models
        return list(models)

    def model(self, model_key: str) -> ModelInfo:
        for model in self.list_models():
            if model.model_key == model_key:
                return model
        raise ProviderError(
            f"Model {model_key!r} is not in the current catalog. Run `--list-models`; do not invent model keys."
        )

    def estimate_cost(self, request: GenerationRequest) -> dict:
        self._validate_request(request)
        data = self._request("POST", "/generations/estimate", payload=request.payload())
        return {
            "model_key": data.get("model_key", request.model_key),
            "operation": data.get("operation", request.operation),
            "estimated_credits": data.get("estimated_credits"),
            "currency": data.get("currency"),
            "raw": data,
        }

    def _validate_request(self, request: GenerationRequest):
        errors = request.validate()
        if errors:
            raise UsageError("; ".join(errors))
        if not request.model_key:
            raise UsageError("model_key is required; discover it with list_models()")
        if not self.config.api_key:
            raise ProviderError("PERCHANCEAI_API_KEY is required")
        model = self.model(request.model_key)
        if not model.supports(request.operation):
            raise UsageError(f"Model {model.model_key} does not support operation {request.operation!r}")
        schema = model.input_schema or {}
        allowed = set((schema.get("properties") or {}).keys())
        # prompt/negative_prompt/reference_upload_ids are top-level request fields;
        # parameters must come from the model's parameter schema when present.
        unknown = set(request.parameters or {}) - allowed if allowed else set()
        unknown -= {"prompt", "negative_prompt", "reference_upload_ids"}
        if unknown:
            raise UsageError(f"Parameters not accepted by {model.model_key}: {sorted(unknown)}")
        return model

    def generate(self, request: GenerationRequest) -> GenerationResult:
        if self.config.mode == "manual":
            return self._manual_handoff(request)
        if self.config.mode == "documented_tutorial":
            raise UnsupportedIntegration(
                "The interface described at https://perchance.org/api-tutorial is not usable: "
                "its documented endpoint /api/generateList.php returned HTTP 404 when tested on 2026-11-12. "
                "Use PERCHANCE_MODE=developer_api with a formal PerchanceAI key, or PERCHANCE_MODE=manual."
            )
        if self.config.mode != "developer_api":
            raise UnsupportedIntegration(f"Unsupported Perchance mode: {self.config.mode}")

        self._validate_request(request)
        if not request.confirmed and self.config.require_approval:
            raise ApprovalRequired(
                "Chargeable generation requires explicit approval. Re-run with --confirm after reviewing the estimate."
            )
        estimate = self.estimate_cost(request)
        estimated = float(estimate.get("estimated_credits") or 0)
        limit = request.budget_credits if request.budget_credits is not None else self.config.max_credits
        if estimated > limit:
            raise BudgetExceeded(f"Estimated {estimated} credits exceeds the configured limit of {limit}")

        idempotency_key = (request.metadata or {}).get("idempotency_key") or str(uuid.uuid4())
        prompt_path = self._write_prompt(request, idempotency_key)
        record = {
            "provider": self.provider_id,
            "mode": self.config.mode,
            "created_at": _utcnow(),
            "idempotency_key": idempotency_key,
            "model_key": request.model_key,
            "operation": request.operation,
            "prompt": request.prompt,
            "negative_prompt": request.negative_prompt,
            "parameters": request.parameters,
            "reference_upload_ids": request.reference_upload_ids,
            "estimated_credits": estimated,
            "status": "submitting",
            "prompt_file": str(prompt_path),
            "asset_id": (request.metadata or {}).get("asset_id"),
        }
        record_path = self._record_path(idempotency_key)
        write_json(record_path, record)
        try:
            data = self._request(
                "POST",
                "/generations",
                payload=request.payload(),
                idempotency_key=idempotency_key,
            )
        except Exception as exc:
            # An uncertain POST must not be blindly retried with a new key: that
            # could bill twice.  Persist the key so a human can retry safely.
            record["status"] = "submission_uncertain"
            record["error"] = str(exc)
            write_json(record_path, record)
            self._append_idempotency(idempotency_key, record)
            raise ProviderError(
                f"Generation submission did not complete. The idempotency key {idempotency_key} was saved in "
                f"{record_path}. Before retrying, check the task status with that key; do not submit a new key blindly. "
                f"Original error: {exc}"
            ) from exc
        result = GenerationResult.from_api(self.provider_id, self.config.mode, data)
        result.prompt_path = str(prompt_path)
        result.record_path = str(record_path)
        record.update({"status": result.status, "generation_id": result.generation_id, "raw": data})
        write_json(record_path, record)
        self._append_idempotency(idempotency_key, record)
        return result

    def get_status(self, generation_id: str) -> GenerationResult:
        if not generation_id:
            raise UsageError("generation_id is required")
        data = self._request("GET", f"/generations/{generation_id}")
        return GenerationResult.from_api(self.provider_id, self.config.mode, data)

    def wait_for_generation(self, generation_id: str, on_poll: Callable[[GenerationResult], None] | None = None) -> GenerationResult:
        result = self.get_status(generation_id)
        for _ in range(self.config.max_polls):
            if on_poll:
                on_poll(result)
            if result.status in {"succeeded", "failed", "cancelled"}:
                return result
            delay = self.config.poll_interval
            raw_delay = (result.raw or {}).get("poll_after_ms")
            if raw_delay:
                delay = max(self.config.poll_interval, float(raw_delay) / 1000.0)
            self._sleep(delay)
            result = self.get_status(generation_id)
        raise ProviderError(f"Generation {generation_id} did not reach a terminal state after {self.config.max_polls} polls")

    def cancel(self, generation_id: str) -> GenerationResult:
        data = self._request("POST", f"/generations/{generation_id}/cancel")
        return GenerationResult.from_api(self.provider_id, self.config.mode, data)

    def download_result(self, result: GenerationResult, destination: str | Path) -> list[Path]:
        destination = Path(destination)
        outputs = result.outputs or []
        if not outputs:
            raise ProviderError("Generation has no downloadable outputs yet")
        saved: list[Path] = []
        is_single_file = destination.suffix.lower() in {".png", ".webp", ".jpg", ".jpeg", ".gif"}
        if is_single_file and len(outputs) > 1:
            destination = destination.parent
            is_single_file = False
        if not is_single_file:
            destination.mkdir(parents=True, exist_ok=True)
        for index, output in enumerate(outputs):
            url = output.get("url")
            if not url:
                continue
            if is_single_file:
                target = destination
            else:
                suffix = Path(urlparse(url).path).suffix or ".png"
                target = destination / f"{result.generation_id or 'generation'}_{index:02d}{suffix}"
                counter = 2
                while target.exists():
                    target = destination / f"{result.generation_id or 'generation'}_{index:02d}_{counter}{suffix}"
                    counter += 1
            target.parent.mkdir(parents=True, exist_ok=True)
            # Output URLs are signed/opaque; never send the API bearer token to
            # a third-party host.
            status, _headers, body = self._transport("GET", url, {"User-Agent": "2d-sprite-studio/1.0"}, None, self.config.timeout)
            if status >= 400:
                raise ProviderError(f"Could not download output {index}: HTTP {status}")
            target.write_bytes(body)
            try:
                with Image.open(target) as image:
                    image.verify()
            except Exception as exc:
                target.unlink(missing_ok=True)
                raise ProviderError(f"Downloaded output is not a valid image: {exc}") from exc
            saved.append(target)
        if not saved:
            raise ProviderError("No usable output URLs were returned")
        write_json(
            destination.with_suffix(".download.json") if is_single_file else destination / "download.json",
            {
                "generation_id": result.generation_id,
                "downloaded_at": _utcnow(),
                "files": [
                    {"path": str(path), "sha256": sha256_file(path), "bytes": path.stat().st_size} for path in saved
                ],
                "provenance": result.to_dict(),
            },
        )
        return saved

    # ------------------------------------------------------------- reference
    def upload_reference(self, path: str | Path, role: str = "reference_image") -> dict:
        path = Path(path)
        if role not in {"reference_image", "start_frame", "end_frame"}:
            raise UsageError("role must be reference_image, start_frame or end_frame")
        data = path.read_bytes()
        media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        prepare = self._request(
            "POST",
            "/uploads",
            payload={
                "filename": path.name,
                "media_type": media_type,
                "byte_size": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
                "role": role,
            },
            idempotency_key=str(uuid.uuid4()),
        )
        upload_url = prepare.get("upload_url")
        method = prepare.get("method", "PUT")
        if not upload_url:
            raise ProviderError("Prepare upload did not return upload_url")
        headers = dict(prepare.get("required_headers") or {})
        status, _headers, body = self._transport(method, upload_url, headers, data, self.config.timeout)
        if status >= 400:
            raise ProviderError(f"Signed upload failed with HTTP {status}: {body[:300]!r}")
        complete = self._request(
            "POST",
            f"/uploads/{prepare['upload_id']}/complete",
            payload={"sha256": hashlib.sha256(data).hexdigest()},
            idempotency_key=str(uuid.uuid4()),
        )
        return complete

    # ---------------------------------------------------------------- manual
    def _manual_handoff(self, request: GenerationRequest) -> GenerationResult:
        errors = request.validate()
        if errors:
            raise UsageError("; ".join(errors))
        key = (request.metadata or {}).get("idempotency_key") or datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
        prompt_path = self._write_prompt(request, key)
        handoff_path = prompt_path.with_suffix(".handoff.md")
        handoff_path.write_text(
            "\n".join(
                [
                    "# Perchance manual generation handoff",
                    "",
                    f"1. Open: {self.config.generator_url}",
                    "2. Paste the prompt below into the generator's prompt field.",
                    "3. Generate, download the result, and import it into the project's `assets/source/` folder.",
                    "4. Run `python tools/inspect_image.py` and `python tools/remove_background.py` on the imported file.",
                    "5. Record the actual provider, model label (if shown), prompt file and source hash in the manifest.",
                    "",
                    "This mode intentionally does not automate the browser or bypass any verification.",
                    "",
                    "## Prompt",
                    "",
                    "```text",
                    request.prompt.strip(),
                    "```",
                    "",
                    f"Negative prompt (if the interface supports it): {request.negative_prompt}" if request.negative_prompt else "",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        return GenerationResult(
            provider=self.provider_id,
            mode="manual",
            status="manual_required",
            model_key=request.model_key or None,
            prompt_path=str(prompt_path),
            note=f"Open {self.config.generator_url}, paste the prepared prompt, then import the downloaded image. Handoff: {handoff_path}",
        )

    def _write_prompt(self, request: GenerationRequest, key: str) -> Path:
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        asset_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", str((request.metadata or {}).get("asset_id") or "prompt"))[:60]
        prompt_path = self.config.output_dir / f"{asset_id}__{key}.prompt.txt"
        prompt_path.write_text(request.prompt.strip() + "\n", encoding="utf-8")
        sidecar = {
            "created_at": _utcnow(),
            "provider": self.provider_id,
            "mode": self.config.mode,
            "model_key": request.model_key or None,
            "operation": request.operation,
            "negative_prompt": request.negative_prompt,
            "parameters": request.parameters,
            "reference_upload_ids": request.reference_upload_ids,
            "asset_id": (request.metadata or {}).get("asset_id"),
        }
        write_json(prompt_path.with_suffix(".prompt.json"), sidecar)
        return prompt_path

    def _record_path(self, key: str) -> Path:
        folder = self.config.output_dir / "records"
        folder.mkdir(parents=True, exist_ok=True)
        return folder / f"{key}.json"

    def _append_idempotency(self, key: str, record: dict):
        self.config.idempotency_store.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config.idempotency_store, "a", encoding="utf-8") as handle:
            handle.write(json.dumps({"key": key, **record}, ensure_ascii=False) + "\n")

    def capabilities(self) -> dict:
        return {
            "provider": self.provider_id,
            "modes": ["developer_api", "manual"],
            "list_models": True,
            "estimate_cost": True,
            "generate": self.config.mode in {"developer_api", "manual"},
            "get_status": self.config.mode == "developer_api",
            "download_result": self.config.mode == "developer_api",
            "async": True,
            "reference_images": True,
            "transparent_background": "prompt-only; verify and process locally",
            "manual_handoff": True,
            "documented_tutorial_endpoint": "unsupported (tested HTTP 404)",
        }
