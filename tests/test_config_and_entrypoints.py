"""Configuration helpers, console entry points and export-profile wiring."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from sprite_studio.config import load_config, quality_profile
from sprite_studio.export import EXPORTERS, documented_profiles
from sprite_studio.timeutil import utcnow

ROOT = Path(__file__).resolve().parents[1]


def test_load_config_reads_registries():
    assert "mock" in load_config("providers")["providers"]
    assert "character" in load_config("quality_profiles")["profiles"]


def test_load_config_missing_file_is_explicit():
    with pytest.raises(FileNotFoundError):
        load_config("does_not_exist")


def test_quality_profile_returns_technical_spec():
    spec = quality_profile("character")
    assert spec["transparency_required"] is True
    assert "padding" in spec
    with pytest.raises(ValueError, match="Unknown QA profile"):
        quality_profile("not_a_profile")


def test_export_profiles_are_documented_and_implemented():
    documented = documented_profiles()
    assert documented == set(EXPORTERS), (
        f"config/export_profiles.yaml and sprite_studio.export.EXPORTERS disagree: "
        f"documented-only={sorted(documented - set(EXPORTERS))}, "
        f"implemented-only={sorted(set(EXPORTERS) - documented)}"
    )


def test_source_date_epoch_makes_timestamps_deterministic(monkeypatch):
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "1700000000")
    assert utcnow() == "2023-11-14T22:13:20+00:00"
    assert utcnow() == utcnow()


def test_all_console_scripts_are_importable():
    """Every declared entry point must resolve to a callable main()."""

    content = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    block = content.split("[project.scripts]", 1)[1].split("\n[", 1)[0]
    targets = []
    for line in block.splitlines():
        if "=" not in line or line.strip().startswith("#"):
            continue
        target = line.split("=", 1)[1].strip().strip('"')
        module_name, func_name = target.split(":")
        targets.append((module_name, func_name))
    assert len(targets) == 20

    for module_name, func_name in targets:
        module = __import__(module_name, fromlist=[func_name])
        assert callable(getattr(module, func_name))


def test_schema_rejects_typos_in_critical_blocks(demo_asset, root):
    import copy

    from sprite_studio.manifest import validate_manifest

    schema = root / "schemas" / "asset_manifest.schema.json"
    good = copy.deepcopy(demo_asset["manifest"])
    assert validate_manifest(good, schema)[0]

    bad_hash = copy.deepcopy(good)
    bad_hash["files"]["frame"][0]["sha256"] = "not-a-hash"
    ok, errors = validate_manifest(bad_hash, schema)
    assert not ok and any("sha256" in error for error in errors)

    bad_qa = copy.deepcopy(good)
    bad_qa["qa"]["human_approved"] = "yes"
    ok, errors = validate_manifest(bad_qa, schema)
    assert not ok and any("human_approved" in error for error in errors)

    unknown_file_key = copy.deepcopy(good)
    unknown_file_key["files"]["frame"][0]["sh256"] = "typo"
    ok, errors = validate_manifest(unknown_file_key, schema)
    assert not ok and any("sh256" in error for error in errors)


def test_tool_shims_still_run():
    """`python tools/<name>.py --help` must keep working after the move."""

    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "inspect_image.py"), "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert "usage:" in result.stdout.lower()


def test_export_manifest_has_no_absolute_report_path(demo_asset, tmp_path):
    from sprite_studio.manifest import merge_qa_report

    manifest_path = demo_asset["manifest_path"]
    merged = merge_qa_report(manifest_path, demo_asset["review_path"])
    assert not Path(merged["qa"]["report"]).is_absolute()
    assert (manifest_path.parent / merged["qa"]["report"]).is_file()
    # Restore the fixture file so later tests see the original manifest.
    manifest_path.write_text(json.dumps(demo_asset["manifest"]), encoding="utf-8")
