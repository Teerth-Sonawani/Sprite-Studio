"""Generic, Godot and Unity export tests."""

from __future__ import annotations

import json

import pytest

from sprite_studio.errors import UnsupportedIntegration
from sprite_studio.export import export_asset, export_godot, export_unity
from sprite_studio.image_utils import sha256_file


def _export_generic(demo_asset, tmp_path):
    manifest = demo_asset["manifest"]
    manifest_path = demo_asset["manifest_path"]
    out = tmp_path / "generic"
    result = export_asset(manifest, manifest_path, "generic_png", out, force=True)
    return result, out


def test_generic_export_copies_files_and_rewrites_relative_manifest(demo_asset, tmp_path):
    result, out = _export_generic(demo_asset, tmp_path)
    assert result["profile"] == "generic_png"
    assert (out / "manifest.json").is_file()
    assert (out / "animations.json").is_file()

    exported = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert exported["asset_root"] == "."
    assert exported["export"]["profile"] == "generic_png"
    checked = 0
    for records in exported["files"].values():
        for record in records:
            path = out / record["path"]
            assert path.is_file(), record["path"]
            assert sha256_file(path) == record["sha256"]
            checked += 1
    assert checked >= 5

    animations = json.loads((out / "animations.json").read_text(encoding="utf-8"))
    assert animations["asset_id"] == "demo"
    assert animations["animations"]["idle"]["frame_count"] == 2
    assert animations["sprite_sheets"]


def test_godot_export_writes_spriteframes_with_regions(demo_asset, tmp_path):
    out = tmp_path / "godot"
    result = export_godot(demo_asset["manifest"], demo_asset["manifest_path"], out, force=True)
    tres = out / "demo.tres"
    assert tres.is_file()
    text = tres.read_text(encoding="utf-8")
    assert '[gd_resource type="SpriteFrames"' in text
    assert '"name": &"idle"' in text
    assert 'region = Rect2(0, 0, 16, 16)' in text
    assert 'region = Rect2(16, 0, 16, 16)' in text
    assert (out / "import_notes.json").is_file()
    assert any(path.endswith("demo.tres") for path in result["files"])


def test_unity_export_writes_slices_and_deterministic_meta(demo_asset, tmp_path):
    out = tmp_path / "unity"
    export_unity(demo_asset["manifest"], demo_asset["manifest_path"], out, force=True)
    slices = json.loads((out / "demo__idle__sheet.slices.json").read_text(encoding="utf-8"))
    assert slices["spriteMode"] == "Multiple"
    assert slices["pixelsPerUnit"] == 100
    frames = slices["animations"]["idle"]["frames"]
    assert [frame["x"] for frame in frames] == [0, 16]
    assert all(frame["w"] == 16 and frame["h"] == 16 for frame in frames)
    meta = (out / "demo__idle__sheet.png.meta").read_text(encoding="utf-8")
    assert "spriteMode: 2" in meta
    assert "alphaIsTransparency: 1" in meta
    assert "guid: " in meta
    assert (out / "import_notes.json").is_file()


def test_export_refuses_non_empty_directory_without_force(demo_asset, tmp_path):
    out = tmp_path / "occupied"
    out.mkdir()
    (out / "keep.txt").write_text("existing", encoding="utf-8")
    with pytest.raises(FileExistsError):
        export_asset(demo_asset["manifest"], demo_asset["manifest_path"], "generic_png", out, force=False)


def test_generic_sheet_exports_only_sheet_and_sidecar(demo_asset, tmp_path):
    out = tmp_path / "sheet_only"
    result = export_asset(demo_asset["manifest"], demo_asset["manifest_path"], "generic_sheet", out, force=True)
    assert result["profile"] == "generic_sheet"
    names = sorted(p.name for p in out.iterdir())
    assert "demo__idle__sheet.png" in names
    assert "demo__idle__sheet.json" in names
    assert "manifest.json" in names
    assert "animations.json" in names
    # The whole point of the profile: no individual frame files.
    assert not any("frame" in name for name in names)
    exported = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert set(exported["files"]) == {"sheet", "sheet_metadata"}


def test_generic_export_fails_loudly_on_missing_file(demo_asset, tmp_path):
    manifest = json.loads(json.dumps(demo_asset["manifest"]))
    manifest["files"]["frame"][0]["path"] = "../assets/approved/demo/frames/does_not_exist.png"
    with pytest.raises(FileNotFoundError, match="does not exist"):
        export_asset(manifest, demo_asset["manifest_path"], "generic_png", tmp_path / "missing", force=True)


def test_export_rejects_absolute_manifest_paths(demo_asset, tmp_path):
    manifest = json.loads(json.dumps(demo_asset["manifest"]))
    manifest["files"]["frame"][0]["path"] = str(demo_asset["frame_paths"][0])
    with pytest.raises(ValueError, match="absolute"):
        export_asset(manifest, demo_asset["manifest_path"], "generic_png", tmp_path / "absolute", force=True)


def test_unknown_profile_and_aseprite_are_honest(demo_asset, tmp_path):
    with pytest.raises(ValueError):
        export_asset(demo_asset["manifest"], demo_asset["manifest_path"], "magic", tmp_path / "magic")
    with pytest.raises(UnsupportedIntegration):
        export_asset(demo_asset["manifest"], demo_asset["manifest_path"], "aseprite", tmp_path / "ase")
