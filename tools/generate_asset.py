#!/usr/bin/env python
"""Provider-aware generation CLI: health, models, estimate, generate, status, download.

No credentials are accepted on the command line.  Set PERCHANCEAI_API_KEY in the
environment.  Chargeable generation requires --confirm and a credit limit.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from providers.base_provider import GenerationRequest, GenerationResult
from providers.provider_registry import create_provider
from sprite_studio.cli import print_result, run
from sprite_studio.image_utils import write_json
from sprite_studio.manifest import _load_structured
from sprite_studio.prompting import build_prompt, negative_prompt


def _parse_params(values: list[str] | None) -> dict:
    params = {}
    for item in values or []:
        if "=" not in item:
            raise ValueError(f"--parameter must be key=value, got {item!r}")
        key, raw = item.split("=", 1)
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            value = raw
        params[key] = value
    return params


def _add_provider(parser):
    parser.add_argument("--provider", default="perchance", help="Provider id from config/providers.yaml")
    parser.add_argument("--mode", help="Provider mode (perchance: manual, developer_api, documented_tutorial)")
    parser.add_argument("--json", action="store_true")


def _add_request(parser, require_prompt=True):
    parser.add_argument("--model", help="Exact model key from `models`; do not guess")
    parser.add_argument("--operation", default="image_generation")
    parser.add_argument("--prompt", help="Prompt text")
    parser.add_argument("--prompt-file", help="Read prompt from a file")
    parser.add_argument("--brief", help="Asset brief YAML/JSON (builds a prompt)")
    parser.add_argument("--style", help="Style profile/guide YAML/JSON")
    parser.add_argument("--negative-prompt", help="Override/generate negative prompt")
    parser.add_argument("--parameter", action="append", help="Model parameter key=value (JSON values allowed)")
    parser.add_argument("--reference-upload", action="append", help="Reference image path; uploads through the provider")
    parser.add_argument("--asset-id", help="Asset id recorded in provenance")
    parser.add_argument("--budget-credits", type=float, help="Maximum credits for this request")


def _request_from_args(args) -> GenerationRequest:
    prompt = args.prompt
    if not prompt and args.prompt_file:
        prompt = Path(args.prompt_file).read_text(encoding="utf-8")
    brief = _load_structured(args.brief) if getattr(args, "brief", None) else {}
    style = _load_structured(args.style) if getattr(args, "style", None) else {}
    if not prompt and brief:
        prompt = build_prompt(brief, style)
    if not prompt:
        raise ValueError("Provide --prompt, --prompt-file or --brief")
    negative = args.negative_prompt
    if negative is None and (brief or style):
        negative = negative_prompt(brief, style)
    return GenerationRequest(
        prompt=prompt,
        model_key=args.model or "",
        operation=args.operation,
        negative_prompt=negative or "",
        parameters=_parse_params(args.parameter),
        reference_upload_ids=[],
        metadata={"asset_id": args.asset_id} if args.asset_id else {},
        budget_credits=args.budget_credits,
        confirmed=bool(getattr(args, "confirm", False)),
    )


def _default_result_path(provider_name: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return Path("projects/example-project/manifests/generations") / f"{provider_name}_{stamp}.json"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    health = sub.add_parser("health", help="Check provider reachability and credential status")
    _add_provider(health)

    models = sub.add_parser("models", help="List models from the provider catalog")
    _add_provider(models)
    models.add_argument("--modality", help="Filter by modality (image/video)")
    models.add_argument("--show-schema", action="store_true", help="Print each model's input schema")

    estimate = sub.add_parser("estimate", help="Estimate credits for a request")
    _add_provider(estimate)
    _add_request(estimate)

    generate = sub.add_parser("generate", help="Submit a generation; may be chargeable")
    _add_provider(generate)
    _add_request(generate)
    generate.add_argument("--confirm", action="store_true", help="Approve the charge shown by `estimate`")
    generate.add_argument("--wait", action="store_true", help="Poll until the task is terminal")
    generate.add_argument("--download-to", help="Download successful outputs to this path")
    generate.add_argument("--result-out", help="Where to write the generation result JSON")

    status = sub.add_parser("status", help="Query a generation task")
    _add_provider(status)
    status.add_argument("--generation-id", required=True)
    status.add_argument("--wait", action="store_true")

    download = sub.add_parser("download", help="Download outputs from a saved result JSON")
    _add_provider(download)
    download.add_argument("--result", required=True)
    download.add_argument("--dest", required=True)

    args = parser.parse_args()

    if args.command == "health":
        provider = create_provider(args.provider, mode=args.mode)
        health_result = provider.health_check()
        data = health_result.to_dict()
        data["capabilities"] = provider.capabilities()
        data["config"] = getattr(provider, "config", None).public_dict() if getattr(provider, "config", None) else None
        if args.json:
            print_result(data, as_json=True)
        else:
            print(f"{data['provider']} ({data['mode']}): {'OK' if data['ok'] else 'DEGRADED'}")
            print(f"  {data['detail']}")
            for error in data["errors"]:
                print(f"  - {error}")
            if data.get("config"):
                print(f"  API key set: {data['config']['has_api_key']}  max credits: {data['config']['max_credits']}")
        return 0 if data["models_available"] else 1

    if args.command == "models":
        provider = create_provider(args.provider, mode=args.mode)
        models_list = provider.list_models()
        if args.modality:
            models_list = [m for m in models_list if m.modality == args.modality]
        data = [
            {
                "model_key": m.model_key,
                "display_name": m.display_name,
                "modality": m.modality,
                "operations": m.operations,
                "price": m.price,
                "price_unit": m.price_unit,
                "limits": m.limits,
                "input_schema": m.input_schema if args.show_schema else None,
            }
            for m in models_list
        ]
        if args.json:
            print_result({"models": data}, as_json=True)
        else:
            for item in data:
                price = f"{item['price']} credits/{item['price_unit']}" if item["price"] is not None else "price not published"
                print(f"{item['model_key']:<36} {item['display_name']:<28} {item['modality']:<6} {price}")
                if item["input_schema"]:
                    print(json.dumps(item["input_schema"], indent=2))
        return 0

    if args.command == "estimate":
        provider = create_provider(args.provider, mode=args.mode)
        request = _request_from_args(args)
        if not request.model_key and args.provider == "mock":
            request.model_key = "mock-shape-v1"
        data = provider.estimate_cost(request)
        if args.json:
            print_result(data, as_json=True)
        else:
            print(f"Estimated credits: {data.get('estimated_credits')} {data.get('currency') or ''}".rstrip())
            print(f"  model: {data.get('model_key')}  operation: {data.get('operation')}")
        return 0

    if args.command == "generate":
        provider = create_provider(args.provider, mode=args.mode)
        request = _request_from_args(args)
        if not request.model_key and args.provider == "mock":
            request.model_key = "mock-shape-v1"
        if args.reference_upload:
            if not hasattr(provider, "upload_reference"):
                raise ValueError(f"Provider {args.provider} does not support reference uploads")
            for path in args.reference_upload:
                completed = provider.upload_reference(path)
                upload_id = completed.get("upload_id")
                if upload_id:
                    request.reference_upload_ids.append(upload_id)
        result = provider.generate(request)
        if args.wait and result.generation_id and hasattr(provider, "wait_for_generation"):
            result = provider.wait_for_generation(result.generation_id)
        result_json = result.to_dict()
        result_path = Path(args.result_out) if args.result_out else _default_result_path(args.provider)
        write_json(result_path, result_json)
        downloaded = []
        if args.download_to and result.status == "succeeded":
            downloaded = [str(p) for p in provider.download_result(result, args.download_to)]
            result_json["downloaded_files"] = downloaded
            write_json(result_path, result_json)
        if args.json:
            print_result(result_json, as_json=True)
        else:
            print(f"Generation status: {result.status}")
            if result.generation_id:
                print(f"  id: {result.generation_id}")
            if result.estimated_credits is not None:
                print(f"  estimated credits: {result.estimated_credits}")
            if result.note:
                print(f"  {result.note}")
            if result.error:
                print(f"  error: {result.error}")
            for path in downloaded:
                print(f"  downloaded: {path}")
            print(f"  result: {result_path}")
            if result.status == "manual_required":
                print("  Next: open the generator, paste the prompt, download the image, then run tools/import_generated.py")
        return 0 if result.status in {"succeeded", "queued", "running", "manual_required"} else 1

    if args.command == "status":
        provider = create_provider(args.provider, mode=args.mode)
        result = provider.wait_for_generation(args.generation_id) if args.wait else provider.get_status(args.generation_id)
        data = result.to_dict()
        print_result(data, as_json=True) if args.json else print(json.dumps(data, indent=2))
        return 0 if result.status in {"succeeded", "queued", "running"} else 1

    if args.command == "download":
        provider = create_provider(args.provider, mode=args.mode)
        data = json.loads(Path(args.result).read_text(encoding="utf-8"))
        result = GenerationResult(
            provider=data.get("provider", args.provider),
            mode=data.get("mode", "unknown"),
            status=data.get("status", "unknown"),
            generation_id=data.get("generation_id"),
            model_key=data.get("model_key"),
            outputs=data.get("outputs", []),
            estimated_credits=data.get("estimated_credits"),
            reserved_credits=data.get("reserved_credits"),
            charged_credits=data.get("charged_credits"),
            error=data.get("error"),
            raw=data.get("raw", {}),
            note=data.get("note"),
        )
        saved = provider.download_result(result, args.dest)
        output = {"files": [str(p) for p in saved]}
        print_result(output, as_json=True) if args.json else print("\n".join(str(p) for p in saved))
        return 0

    raise ValueError(f"Unknown command {args.command}")


if __name__ == "__main__":
    raise SystemExit(run(main))
