"""Engine-independent and engine-specific export helpers.

Every profile documents what it actually writes.  No profile claims to emit a
native editable file when the required application is unavailable.
"""

from __future__ import annotations

import copy
import json
import re
import shutil
from pathlib import Path

from .errors import UnsupportedIntegration
from .image_utils import sha256_file, write_json
from .timeutil import utcnow as _now


def _copy(src: Path, dest: Path, force: bool = False) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and not force:
        raise FileExistsError(f"Refusing to overwrite {dest}. Pass --force.")
    shutil.copy2(src, dest)
    return dest


def _manifest_files(manifest: dict) -> list[dict]:
    files = manifest.get("files", {})
    out = []
    for role, records in files.items():
        for record in records:
            out.append({"role": role, **record})
    return out


def _resolve_record_path(record: dict, manifest: dict, manifest_path: Path) -> Path:
    """Resolve a manifest file record to an existing file.

    Paths are relative to the manifest folder, or to `asset_root` when the
    manifest declares one.  Absolute paths and paths relative to the current
    working directory are rejected: a manifest has to be portable, and resolving
    against the caller's cwd is how an export silently picks up the wrong file.
    """

    raw = Path(record["path"])
    if raw.is_absolute():
        raise ValueError(
            f"Manifest path for role {record.get('role')!r} is absolute ({raw}). "
            "Regenerate the manifest so it stores a path relative to the manifest."
        )
    candidates = [manifest_path.parent / raw]
    asset_root = manifest.get("asset_root")
    if asset_root:
        root = Path(asset_root)
        if root.is_absolute():
            raise ValueError(
                f"Manifest asset_root is absolute ({root}). Regenerate the manifest with a relative asset_root."
            )
        candidates.append(manifest_path.parent / root / raw)
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise FileNotFoundError(
        f"Manifest file for role {record.get('role')!r} does not exist: {raw}. "
        "Tried: " + ", ".join(str(candidate) for candidate in candidates)
    )


def _sheet_metadata(sheet_path: Path) -> dict | None:
    candidates = [sheet_path.with_suffix(".json"), sheet_path.with_name(sheet_path.stem + "_frames.json")]
    for path in candidates:
        if path.is_file():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return None
    return None


def _frame_rect(frame: dict) -> dict:
    """Use the full cell rect so transparent padding keeps frame alignment."""

    if "cell_width" in frame and "cell_height" in frame:
        return {
            "x": frame.get("cell_x", 0),
            "y": frame.get("cell_y", 0),
            "w": frame["cell_width"],
            "h": frame["cell_height"],
        }
    return {
        "x": frame.get("x", 0),
        "y": frame.get("y", 0),
        "w": frame.get("w", frame.get("width", 0)),
        "h": frame.get("h", frame.get("height", 0)),
    }


def _animation_regions(manifest: dict, sheet_path: Path) -> dict:
    """Build animation regions from a sheet's sidecar metadata when available.

    A manifest animation may declare `sheet` to bind it to one sheet and
    `frame_start` when several animations share a sheet.  Without a binding, the
    animation is used only when the manifest has a single sheet; otherwise a
    default whole-sheet animation is emitted for that sheet.
    """

    meta = _sheet_metadata(sheet_path)
    if not meta:
        return {}
    frames = meta.get("frames", [])
    animations = manifest.get("animations", {})
    sheets = manifest.get("files", {}).get("sheet", [])
    result: dict = {}
    if animations:
        for name, spec in animations.items():
            declared_sheet = spec.get("sheet")
            if declared_sheet:
                declared = Path(str(declared_sheet)).name
                if declared not in {sheet_path.name, sheet_path.stem}:
                    continue
            elif len(sheets) > 1:
                # Ambiguous: do not attach every animation to every sheet.
                continue
            count = int(spec.get("frame_count") or len(frames))
            start = max(0, int(spec.get("frame_start", 0) or 0))
            durations = spec.get("durations_ms") or []
            selected = frames[start : start + count]
            if not selected:
                continue
            fallback_ms = int(1000 / max(1.0, float(spec.get("frame_rate", 10))))
            entries = []
            for i, frame in enumerate(selected):
                rect = _frame_rect(frame)
                rect["duration_ms"] = (
                    int(durations[i]) if i < len(durations) else int(frame.get("duration_ms", fallback_ms))
                )
                entries.append(rect)
            result[name] = {
                "loop": bool(spec.get("loop", True)),
                "fps": float(spec.get("frame_rate", 10)),
                "frames": entries,
            }
    if not result:
        result["default"] = {
            "loop": True,
            "fps": 10,
            "frames": [
                {
                    **_frame_rect(frame),
                    "duration_ms": int(frame.get("duration_ms", 100)),
                }
                for frame in frames
            ],
        }
    return result


def export_generic(manifest: dict, manifest_path: Path, out_dir: Path, force: bool = False) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    exported_files: dict[str, list[dict]] = {}
    for record in _manifest_files(manifest):
        path = _resolve_record_path(record, manifest, manifest_path)
        dest = out_dir / record["role"] / path.name
        written.append(str(_copy(path, dest, force=force)))
        updated = copy.deepcopy(record)
        updated["path"] = f"{record['role']}/{path.name}"
        updated["filename"] = path.name
        exported_files.setdefault(record["role"], []).append(updated)

    export_manifest = copy.deepcopy(manifest)
    export_manifest["files"] = exported_files
    export_manifest["asset_root"] = "."
    export_manifest["export"] = {
        "profile": "generic_png",
        "exported_at": _now(),
        "note": "File paths in this copy are relative to this export folder.",
    }
    manifest_dest = out_dir / "manifest.json"
    write_json(manifest_dest, export_manifest)
    written.append(str(manifest_dest))
    animation_export = {
        "asset_id": manifest.get("asset_id"),
        "name": manifest.get("name"),
        "width": manifest.get("width"),
        "height": manifest.get("height"),
        "pivot": manifest.get("pivot"),
        "animations": manifest.get("animations", {}),
        "sprite_sheets": [r["path"] for records in exported_files.values() for r in records if r["role"] == "sheet"],
        "frames": [r["path"] for records in exported_files.values() for r in records if r["role"] == "frame"],
    }
    anim_path = out_dir / "animations.json"
    write_json(anim_path, animation_export)
    written.append(str(anim_path))
    return {"profile": "generic_png", "output_dir": str(out_dir), "files": written}


def export_generic_sheet(manifest: dict, manifest_path: Path, out_dir: Path, force: bool = False) -> dict:
    """Export only the sprite sheet(s), their sidecars and the animation metadata.

    This is deliberately different from `generic_png`: individual frames are not
    copied.  The sheet plus its sidecar JSON is the authoritative artefact, which
    is what engines that consume sheets expect.
    """

    sheets = manifest.get("files", {}).get("sheet", [])
    if not sheets:
        raise ValueError("generic_sheet requires at least one sprite sheet record")
    out_dir.mkdir(parents=True, exist_ok=True)
    wanted = {"sheet", "sheet_metadata"}
    written = []
    exported_files: dict[str, list[dict]] = {}
    for record in _manifest_files(manifest):
        if record["role"] not in wanted:
            continue
        path = _resolve_record_path(record, manifest, manifest_path)
        dest = out_dir / path.name
        written.append(str(_copy(path, dest, force=force)))
        updated = copy.deepcopy(record)
        updated["path"] = path.name
        updated["filename"] = path.name
        exported_files.setdefault(record["role"], []).append(updated)

    if "sheet" not in exported_files:
        raise ValueError("generic_sheet found no resolvable sprite sheet records")

    export_manifest = copy.deepcopy(manifest)
    export_manifest["files"] = exported_files
    export_manifest["asset_root"] = "."
    export_manifest["export"] = {
        "profile": "generic_sheet",
        "exported_at": _now(),
        "note": "Sheet and sidecar paths are relative to this export folder; frames are not copied.",
    }
    manifest_dest = out_dir / "manifest.json"
    write_json(manifest_dest, export_manifest)
    written.append(str(manifest_dest))

    animation_export = {
        "asset_id": manifest.get("asset_id"),
        "name": manifest.get("name"),
        "width": manifest.get("width"),
        "height": manifest.get("height"),
        "pivot": manifest.get("pivot"),
        "animations": manifest.get("animations", {}),
        "sprite_sheets": [record["path"] for record in exported_files["sheet"]],
    }
    anim_path = out_dir / "animations.json"
    write_json(anim_path, animation_export)
    written.append(str(anim_path))

    notes_path = out_dir / "import_notes.json"
    write_json(notes_path, {
        "profile": "generic_sheet",
        "note": "Frame rects and durations live in the sheet sidecar JSON next to each PNG.",
        "limitations": [
            "No individual frame files are exported; rebuild the sheet if a frame changes.",
        ],
    })
    written.append(str(notes_path))
    return {"profile": "generic_sheet", "output_dir": str(out_dir), "files": written}


def export_godot(manifest: dict, manifest_path: Path, out_dir: Path, force: bool = False) -> dict:
    """Write a SpriteFrames .tres and the referenced textures.

    This is a practical Godot 4 resource, not a fake placeholder.  It assumes the
    exported folder is copied into the Godot project as a unit.
    """

    out_dir.mkdir(parents=True, exist_ok=True)
    sheets = manifest.get("files", {}).get("sheet", [])
    if not sheets:
        raise ValueError("Godot SpriteFrames export requires at least one sprite sheet record")
    written = []
    copied: list[tuple[dict, Path]] = []
    for record in sheets:
        src = _resolve_record_path(record, manifest, manifest_path)
        if not src.is_file():
            raise FileNotFoundError(f"Sprite sheet listed in manifest does not exist: {src}")
        dest = out_dir / src.name
        written.append(str(_copy(src, dest, force=force)))
        copied.append((record, src))

    ext_lines: list[str] = []
    sub_lines: list[str] = []
    animation_entries: list[str] = []
    for sheet_index, (record, src) in enumerate(copied, start=1):
        ext_id = f"{sheet_index}_texture"
        ext_lines.append(
            f'[ext_resource type="Texture2D" path="res://{src.name}" id="{ext_id}"]'
        )
        regions = _animation_regions(manifest, src)
        for anim_index, (anim_name, anim) in enumerate(regions.items()):
            frame_entries = []
            for frame_index, frame in enumerate(anim["frames"]):
                safe_anim = re.sub(r"[^A-Za-z0-9_]+", "_", anim_name) or "animation"
                sub_id = f"AtlasTexture_{sheet_index}_{safe_anim}_{frame_index:03d}"
                sub_lines.append(f'[sub_resource type="AtlasTexture" id="{sub_id}"]')
                sub_lines.append(f'atlas = ExtResource("{ext_id}")')
                sub_lines.append(
                    f'region = Rect2({frame["x"]}, {frame["y"]}, {frame["w"]}, {frame["h"]})'
                )
                sub_lines.append("")
                frame_entries.append(
                    '{\n"duration": %.3f,\n"texture": SubResource("%s")\n}'
                    % (frame["duration_ms"] / 1000.0, sub_id)
                )
            animation_entries.append(
                '{\n"frames": [%s],\n"loop": %s,\n"name": &"%s",\n"speed": %.3f\n}'
                % (
                    ", ".join(frame_entries),
                    "true" if anim["loop"] else "false",
                    str(anim_name).replace('"', '\\"'),
                    anim["fps"],
                )
            )

    # Godot requires every ext_resource/sub_resource before [resource].
    load_steps = len(ext_lines) + len([line for line in sub_lines if line.startswith("[sub_resource")]) + 1
    lines = [f'[gd_resource type="SpriteFrames" load_steps={load_steps} format=3]']
    lines.extend(ext_lines)
    lines.append("")
    lines.extend(sub_lines)
    lines.append("[resource]")
    lines.append("animations = [%s]" % ", ".join(animation_entries))
    lines.append("")
    tres_path = out_dir / f"{manifest.get('asset_id', 'asset')}.tres"
    if tres_path.exists() and not force:
        raise FileExistsError(f"Refusing to overwrite {tres_path}. Pass --force.")
    tres_path.write_text("\n".join(lines), encoding="utf-8")
    written.append(str(tres_path))
    write_json(out_dir / "import_notes.json", {
        "engine": "Godot 4.x",
        "texture_filter": "Nearest for pixel art; Linear for painted art",
        "sprite_frames": tres_path.name,
        "note": "Copy the folder into the Godot project and keep the .tres and PNGs together.",
        "limitations": [
            "Animation names come from the manifest; verify frame order and loop flags in the Godot inspector.",
            "If a sheet is rebuilt, regenerate the .tres rather than hand-editing regions.",
        ],
    })
    written.append(str(out_dir / "import_notes.json"))
    return {"profile": "godot_4", "output_dir": str(out_dir), "files": written}


def export_unity(manifest: dict, manifest_path: Path, out_dir: Path, force: bool = False) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    sheets = manifest.get("files", {}).get("sheet", [])
    if not sheets:
        raise ValueError("Unity export requires at least one sprite sheet")
    written = []
    for record in sheets:
        src = _resolve_record_path(record, manifest, manifest_path)
        if not src.is_file():
            raise FileNotFoundError(f"Sprite sheet listed in manifest does not exist: {src}")
        dest = out_dir / src.name
        written.append(str(_copy(src, dest, force=force)))
        regions = _animation_regions(manifest, src)
        slicing = {
            "texture": dest.name,
            "spriteMode": "Multiple",
            "pixelsPerUnit": 100,
            "filterMode": "Point",
            "alphaIsTransparency": True,
            "animations": regions,
            "note": "Import the PNG, set Sprite Mode to Multiple, then apply these rects in the Sprite Editor or via the provided JSON.",
        }
        slice_path = out_dir / f"{dest.stem}.slices.json"
        write_json(slice_path, slicing)
        written.append(str(slice_path))
        meta = _unity_meta(manifest, dest, slicing)
        meta_path = out_dir / f"{dest.name}.meta"
        if meta_path.exists() and not force:
            raise FileExistsError(f"Refusing to overwrite {meta_path}. Pass --force.")
        meta_path.write_text(meta, encoding="utf-8")
        written.append(str(meta_path))
    write_json(out_dir / "import_notes.json", {
        "engine": "Unity 2022.3+",
        "texture_type": "Sprite (2D and UI)",
        "sprite_mode": "Multiple",
        "filter_mode": "Point (for pixel art) or Bilinear (for painted art)",
        "pixels_per_unit": 100,
        "note": "Unity does not consume a portable sprite-sheet metadata format. Apply the JSON rects in the Sprite Editor or through an editor script.",
    })
    written.append(str(out_dir / "import_notes.json"))
    return {"profile": "unity_2022", "output_dir": str(out_dir), "files": written}


def _unity_meta(manifest: dict, texture: Path, slicing: dict) -> str:
    # Deterministic GUID from content + asset id so repeated exports are stable.
    import hashlib

    guid = hashlib.md5((sha256_file(texture) + str(manifest.get("asset_id"))).encode()).hexdigest()
    return f"""fileFormatVersion: 2
guid: {guid}
TextureImporter:
  internalIDToNameTable: []
  externalObjects: {{}}
  serializedVersion: 12
  mipmaps:
    mipMapMode: 0
    enableMipMap: 0
  isReadable: 0
  streamingMipmaps: 0
  textureFormat: 1
  maxTextureSize: 2048
  textureSettings:
    serializedVersion: 2
    filterMode: 0
    aniso: 1
    mipBias: 0
    wrapU: 1
    wrapV: 1
  nPOTScale: 0
  lightmap: 0
  compressionQuality: 50
  spriteMode: 2
  spriteExtrude: 1
  spriteMeshType: 1
  alignment: 0
  spritePivot: {{x: 0.5, y: 0.0}}
  spritePixelsToUnits: 100
  spriteBorder: {{x: 0, y: 0, z: 0, w: 0}}
  alphaIsTransparency: 1
  textureType: 8
  textureShape: 1
  singleChannelComponent: 0
  flipbookRows: 1
  flipbookColumns: 1
  maxTextureSizeSet: 0
  compressionQualitySet: 0
  textureFormatSet: 0
  ignorePngGamma: 0
  applyGammaDecoding: 0
  platformSettings: []
  spriteSheet:
    serializedVersion: 2
    sprites: []
    outline: []
    physicsShape: []
    bones: []
    spriteID: 5e97eb03825dee720800000000000000
    internalID: 0
    vertices: []
    indices: []
    edges: []
    weights: []
  spritePackingTag: 
  pSDRemoveMatte: 0
  pSDShowRemoveMatteOption: 0
  userData: 
  assetBundleName: 
  assetBundleVariant: 
"""


def export_aseprite(manifest: dict, manifest_path: Path, out_dir: Path, force: bool = False) -> dict:
    """Only supported when an Aseprite/LibreSprite CLI is installed."""

    exe = shutil.which("aseprite") or shutil.which("libresprite")
    if not exe:
        raise UnsupportedIntegration(
            "Aseprite/LibreSprite CLI not found. Export PNG frames and a sheet instead; "
            "an editable .ase/.aseprite file cannot be created without the application."
        )
    raise UnsupportedIntegration(
        f"Found {exe}, but this workspace does not implement a native .aseprite project writer. "
        "Use Aseprite's own script/CLI or export PNG frames."
    )


EXPORTERS = {
    "generic_png": export_generic,
    "generic_sheet": export_generic_sheet,
    "godot_4": export_godot,
    "unity_2022": export_unity,
    "aseprite": export_aseprite,
}


def documented_profiles(config_path: str | Path | None = None) -> set[str]:
    """Profile names documented in `config/export_profiles.yaml`.

    Returns an empty set when the configuration file is unavailable, so the
    library keeps working outside a source checkout.
    """

    from .config import load_config, load_yaml

    try:
        data = load_yaml(config_path) if config_path else load_config("export_profiles")
    except FileNotFoundError:
        return set()
    return set((data.get("profiles") or {}).keys())


def export_asset(manifest: dict, manifest_path: str | Path, profile: str, out_dir: str | Path, force: bool = False) -> dict:
    if profile not in EXPORTERS:
        raise ValueError(f"Unknown export profile {profile!r}; choose from {sorted(EXPORTERS)}")
    documented = documented_profiles()
    if documented and profile not in documented:
        raise ValueError(
            f"Export profile {profile!r} is implemented but not documented in config/export_profiles.yaml. "
            "Document it before use so the written files are predictable."
        )
    manifest_path = Path(manifest_path)
    out_dir = Path(out_dir)
    if out_dir.exists() and any(out_dir.iterdir()) and not force:
        raise FileExistsError(f"Export directory {out_dir} is not empty. Pass --force to replace files.")
    return EXPORTERS[profile](manifest, manifest_path, out_dir, force=force)
