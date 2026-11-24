"""Asset manifest construction and validation."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable

import yaml

from .image_utils import alpha_stats, load_image, sha256_file, write_json
from .timeutil import utcnow as _utcnow

MANIFEST_VERSION = "1.0"


def _load_structured(path: str | Path | None) -> dict:
    if not path:
        return {}
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Structured file not found: {path}")
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        data = yaml.safe_load(text) or {}
    elif path.suffix.lower() == ".json":
        data = json.loads(text)
    else:
        raise ValueError(f"Expected .yaml/.yml/.json, got {path.suffix}")
    if not isinstance(data, dict):
        raise ValueError(f"Expected a mapping at the top level of {path}")
    return data


def _relative_path(path: Path, base: Path | None) -> str:
    """Return a portable, forward-slash path relative to `base` when possible."""

    if base is not None:
        try:
            return Path(os.path.relpath(path.resolve(), base.resolve())).as_posix()
        except ValueError:
            pass
    return path.as_posix()


def _image_record(path: Path, role: str, path_base: Path | None = None) -> dict:
    image = load_image(path, None)
    rgba = image.convert("RGBA")
    stats = alpha_stats(rgba)
    record = {
        "role": role,
        "path": _relative_path(path, path_base),
        "filename": path.name,
        "format": (image.format or path.suffix.lstrip(".")).lower(),
        "width": image.width,
        "height": image.height,
        "mode": image.mode,
        "transparent": stats["transparent_pixels"] > 0,
        "alpha_coverage": stats["coverage"],
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }
    if role == "frame":
        record["bbox"] = stats["bbox"]
    return record


def _sidecar_record(path: Path, role: str, path_base: Path | None = None) -> dict:
    """Record a JSON sidecar without pretending it is an image."""

    return {
        "role": role,
        "path": _relative_path(path, path_base),
        "filename": path.name,
        "format": "json",
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _discover_files(
    asset_dir: Path,
    roles: dict[str, Iterable[str]] | None = None,
    path_base: Path | None = None,
) -> dict[str, list[dict]]:
    roles = roles or {
        "source": ["source", "concepts"],
        "frame": ["frames", "approved"],
        "sheet": ["spritesheets", "sheets"],
        "sheet_metadata": ["spritesheets", "sheets"],
        "preview": ["previews"],
        "atlas": ["atlas"],
        "atlas_metadata": ["atlas"],
    }
    found: dict[str, list[dict]] = {role: [] for role in roles}
    for role, folder_names in roles.items():
        suffixes = {".json"} if role.endswith("_metadata") else {".png", ".webp", ".gif"}
        for folder_name in folder_names:
            folder = asset_dir / folder_name
            if not folder.is_dir():
                continue
            for path in sorted(folder.rglob("*")):
                if path.is_file() and path.suffix.lower() in suffixes:
                    if role.endswith("_metadata"):
                        found[role].append(_sidecar_record(path, role, path_base))
                    else:
                        found[role].append(_image_record(path, role, path_base))
    # De-duplicate by path.
    for role, records in found.items():
        seen = set()
        unique = []
        for record in records:
            if record["path"] not in seen:
                seen.add(record["path"])
                unique.append(record)
        found[role] = unique
    return found


def _animation_metadata(animations_dir: Path | None, asset_id: str | None = None) -> dict:
    result: dict[str, dict] = {}
    if not animations_dir or not animations_dir.is_dir():
        return result
    for path in sorted(animations_dir.glob("*.y*ml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            continue
        spec_asset = data.get("asset_id")
        if asset_id and spec_asset and str(spec_asset) != str(asset_id):
            continue
        name = data.get("animation_name") or data.get("animation_id")
        if not name:
            continue
        frames = data.get("frame_sequence") or []
        durations = [int(f.get("duration_ms", round(1000 / float(data.get("frame_rate", 10))))) for f in frames] if frames else []
        result[name] = {
            "spec": str(path.name),
            "frame_count": int(data.get("frame_count") or len(frames) or 0),
            "frame_rate": float(data.get("frame_rate", 10)),
            "loop": bool(data.get("loop", True)),
            "loop_type": data.get("loop_type", "loop" if data.get("loop", True) else "once"),
            "direction": data.get("direction", "side"),
            "durations_ms": durations,
            "frames": [f.get("frame") for f in frames] if frames else [],
            "frame_start": int(data.get("frame_start", 0) or 0),
            "sheet": data.get("sheet") or data.get("sprite_sheet"),
            "notes": data.get("movement_description", ""),
        }
    return result


def build_manifest(
    asset_dir: str | Path,
    brief_path: str | Path | None = None,
    style_path: str | Path | None = None,
    animations_dir: str | Path | None = None,
    qa_report_path: str | Path | None = None,
    provenance: dict | None = None,
    asset_id: str | None = None,
    name: str | None = None,
    category: str | None = None,
    output_path: str | Path | None = None,
    path_base: str | Path | None = None,
) -> dict:
    asset_dir = Path(asset_dir)
    if not asset_dir.is_dir():
        raise NotADirectoryError(f"Asset directory not found: {asset_dir}")
    path_base = Path(path_base).resolve() if path_base else None
    brief = _load_structured(brief_path)
    style = _load_structured(style_path)
    qa_report = _load_structured(qa_report_path) if qa_report_path else {}
    files = _discover_files(asset_dir, path_base=path_base)
    frames = files.get("frame", [])
    sheets = files.get("sheet", [])
    resolved_asset_id = asset_id or brief.get("asset_id") or asset_dir.name

    if not frames and not sheets:
        raise ValueError(f"No frame or spritesheet PNGs found under {asset_dir}")

    chosen = next((r for r in frames if r.get("bbox")), None)
    if chosen:
        width, height = chosen["width"], chosen["height"]
        transparent = chosen["transparent"]
        mode = chosen["mode"]
    else:
        first = sheets[0]
        width, height = first["width"], first["height"]
        transparent = first["transparent"]
        mode = first["mode"]

    qa_status = qa_report.get("qa_status") or qa_report.get("technical_status") or "PENDING"
    technical_status = qa_report.get("technical_status") or "PENDING"
    visual_status = qa_report.get("visual_status") or "NOT_REVIEWED"
    human_approved = bool(qa_report.get("human_approved", False))
    if qa_report_path and not qa_report:
        qa_status = "PENDING"

    provenance = dict(provenance or {})
    if not provenance:
        provenance = {
            "provider": "unknown",
            "mode": "unrecorded",
            "model_key": None,
            "generation_id": None,
            "prompt": None,
            "source_files": [r["path"] for r in files.get("source", [])],
            "notes": "Provenance must be supplied by the generation/import stage.",
        }
    provenance.setdefault("created_at", _utcnow())
    provenance.setdefault("license", brief.get("license", "Original project asset; verify before distribution."))

    manifest = {
        "manifest_version": MANIFEST_VERSION,
        "asset_id": resolved_asset_id,
        "asset_root": _relative_path(asset_dir, path_base) if path_base else ".",
        "name": name or brief.get("asset_name") or asset_dir.name.replace("_", " ").title(),
        "category": category or brief.get("asset_category") or "unspecified",
        "subcategory": brief.get("asset_subcategory"),
        "description": brief.get("description", ""),
        "project": brief.get("intended_game", ""),
        "intended_use": brief.get("intended_use", ""),
        "style_id": style.get("style_id") or brief.get("art_style") or "unspecified",
        "intended_engine": brief.get("target_engine", "generic"),
        "export_format": brief.get("export_format", "png"),
        "file_format": "png",
        "width": width,
        "height": height,
        "colour_mode": mode,
        "transparent": transparent,
        "pivot": brief.get("pivot") or {"x": width // 2, "y": height},
        "anchor_point": brief.get("anchor_point", "bottom-center"),
        "ground_contact": brief.get("ground_contact", None),
        "files": files,
        "animations": _animation_metadata(
            Path(animations_dir) if animations_dir else None, asset_id=resolved_asset_id
        ),
        "qa": {
            "technical_status": technical_status,
            "visual_status": visual_status,
            "qa_status": qa_status,
            "human_approved": human_approved,
            "report": (
                _relative_path(
                    Path(qa_report_path),
                    path_base or (Path(output_path).parent if output_path else None),
                )
                if qa_report_path
                else None
            ),
            "review": qa_report.get("review"),
        },
        "provenance": provenance,
        "created_at": _utcnow(),
        "updated_at": _utcnow(),
    }

    if output_path:
        write_json(output_path, manifest)
    return manifest


def validate_manifest(manifest: dict, schema_path: str | Path | None = None) -> tuple[bool, list[str]]:
    errors: list[str] = []
    required = ["manifest_version", "asset_id", "name", "category", "width", "height", "files", "qa"]
    for key in required:
        if key not in manifest:
            errors.append(f"missing required field: {key}")
    if manifest.get("width", 0) <= 0 or manifest.get("height", 0) <= 0:
        errors.append("width and height must be positive")
    if not isinstance(manifest.get("files"), dict):
        errors.append("files must be an object")
    qa = manifest.get("qa", {})
    if qa.get("qa_status") not in {"PENDING", "TECHNICAL_PASS", "VISUAL_REVIEW", "APPROVED", "REJECTED", "NOT_REVIEWED"}:
        errors.append(f"invalid qa_status: {qa.get('qa_status')}")
    if qa.get("qa_status") == "APPROVED" and qa.get("technical_status") not in {"TECHNICAL_PASS", "APPROVED"}:
        errors.append("manifest cannot be APPROVED without a technical pass")
    if qa.get("human_approved") and qa.get("qa_status") != "APPROVED":
        errors.append("human_approved requires qa_status APPROVED")

    if schema_path:
        try:
            import jsonschema  # type: ignore

            schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
            jsonschema.validate(manifest, schema)
        except ImportError:
            errors.append("jsonschema is not installed; schema validation skipped")
        except Exception as exc:
            errors.append(f"schema validation failed: {exc}")
    return (len(errors) == 0), errors


def merge_qa_report(manifest_path: str | Path, qa_report_path: str | Path, output_path: str | Path | None = None) -> dict:
    """Merge a QA report into an existing manifest.

    The stored report path is relative to the manifest so the result stays
    portable across machines and checkouts.
    """

    manifest_path = Path(manifest_path)
    qa_report_path = Path(qa_report_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    qa = json.loads(qa_report_path.read_text(encoding="utf-8"))
    target = Path(output_path) if output_path else manifest_path
    manifest["qa"] = {
        "technical_status": qa.get("technical_status", "PENDING"),
        "visual_status": qa.get("visual_status", "NOT_REVIEWED"),
        "qa_status": qa.get("qa_status", "PENDING"),
        "human_approved": bool(qa.get("human_approved", False)),
        "report": _relative_path(qa_report_path, target.parent),
        "review": qa.get("review"),
    }
    manifest["updated_at"] = _utcnow()
    write_json(target, manifest)
    return manifest
