"""Acceptance tests that exercise the actual CLI entry points."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def run_tool(*args: str, timeout: int = 120, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, *args],
        cwd=cwd or ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _frame(size=(16, 16), offset=0) -> Image.Image:
    from PIL import ImageDraw

    image = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(image).ellipse((3, 5 + offset, 12, 13 + offset), fill=(80, 140, 90, 255))
    return image


def test_inspect_and_validate_cli(tmp_path):
    image_path = tmp_path / "frame.png"
    _frame().save(image_path)
    report_path = tmp_path / "report.json"

    inspected = run_tool(str(ROOT / "tools" / "inspect_image.py"), str(image_path), "--palette", "--json")
    assert inspected.returncode == 0, inspected.stderr
    info = json.loads(inspected.stdout)
    assert info["width"] == 16 and info["height"] == 16
    assert info["alpha"]["coverage"] > 0

    validated = run_tool(
        str(ROOT / "tools" / "validate_sprite.py"),
        str(image_path),
        "--width",
        "16",
        "--height",
        "16",
        "--transparency",
        "--padding",
        "2",
        "--pivot-x",
        "8",
        "--pivot-y",
        "14",
        "--report",
        str(report_path),
        "--json",
    )
    assert validated.returncode == 0, validated.stderr
    report = json.loads(validated.stdout)
    assert report["technical_status"] == "TECHNICAL_PASS"
    assert report_path.is_file()


def test_build_sheet_and_record_review_cli(tmp_path):
    frame_dir = tmp_path / "frames"
    frame_dir.mkdir()
    for index in range(3):
        _frame(offset=index % 2).save(frame_dir / f"frame_{index:03d}.png")

    sheet_path = tmp_path / "sheet.png"
    metadata_path = tmp_path / "sheet.json"
    built = run_tool(
        str(ROOT / "tools" / "build_spritesheet.py"),
        str(frame_dir),
        "--output",
        str(sheet_path),
        "--metadata",
        str(metadata_path),
        "--layout",
        "horizontal",
        "--cell-width",
        "16",
        "--cell-height",
        "16",
        "--durations",
        "100,100,100",
        "--json",
    )
    assert built.returncode == 0, built.stderr
    assert sheet_path.is_file()
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["frame_count"] == 3

    technical_path = tmp_path / "technical.json"
    validated = run_tool(
        str(ROOT / "tools" / "validate_sprite.py"),
        str(frame_dir / "frame_000.png"),
        "--width",
        "16",
        "--height",
        "16",
        "--transparency",
        "--padding",
        "2",
        "--report",
        str(technical_path),
        "--json",
    )
    assert validated.returncode == 0, validated.stderr

    review_path = tmp_path / "review.json"
    reviewed = run_tool(
        str(ROOT / "tools" / "qa_review.py"),
        str(technical_path),
        "--decision",
        "approve",
        "--reviewer",
        "cli-test",
        "--evidence",
        str(sheet_path),
        "--score",
        "silhouette=4",
        "--output",
        str(review_path),
    )
    assert reviewed.returncode == 0, reviewed.stderr
    review = json.loads(review_path.read_text(encoding="utf-8"))
    assert review["qa_status"] == "APPROVED"
    assert review["human_approved"] is False


def test_mock_provider_generate_and_import_cli(tmp_path):
    result_path = tmp_path / "result.json"
    output_path = tmp_path / "mock.png"
    generated = run_tool(
        str(ROOT / "tools" / "generate_asset.py"),
        "generate",
        "--provider",
        "mock",
        "--prompt",
        "original geometric test sprite",
        "--parameter",
        "width=32",
        "--parameter",
        "height=32",
        "--result-out",
        str(result_path),
        "--download-to",
        str(output_path),
        "--json",
        cwd=tmp_path,
    )
    assert generated.returncode == 0, generated.stderr
    assert output_path.is_file()
    with Image.open(output_path) as image:
        assert image.size == (32, 32)
    result = json.loads(result_path.read_text(encoding="utf-8"))
    assert result["status"] == "succeeded"
    assert result["provider"] == "mock"

    source_dir = tmp_path / "source"
    imported = run_tool(
        str(ROOT / "tools" / "import_generated.py"),
        str(output_path),
        "--dest",
        str(source_dir),
        "--asset-id",
        "mock_demo",
        "--provider",
        "mock",
        "--mode",
        "offline",
        "--json",
    )
    assert imported.returncode == 0, imported.stderr
    provenance = json.loads(imported.stdout)
    assert provenance["asset_id"] == "mock_demo"
    sidecar = Path(provenance["stored_path"]).with_suffix(".png.provenance.json")
    assert sidecar.is_file()


def test_export_cli_uses_approved_demo_manifest(tmp_path):
    manifest_path = ROOT / "projects" / "example-project" / "manifests" / "moss_slime.manifest.json"
    if not manifest_path.is_file():
        pytest.skip("demo manifest has not been generated")
    out_dir = tmp_path / "export"
    exported = run_tool(
        str(ROOT / "tools" / "export_asset.py"),
        str(manifest_path),
        "--profile",
        "generic_png",
        "--out",
        str(out_dir),
        "--force",
    )
    assert exported.returncode == 0, exported.stderr
    assert (out_dir / "manifest.json").is_file()
    assert (out_dir / "animations.json").is_file()


def test_export_cli_refuses_unapproved_manifest(tmp_path):
    manifest_path = ROOT / "projects" / "example-project" / "manifests" / "moss_slime.manifest.json"
    if not manifest_path.is_file():
        pytest.skip("demo manifest has not been generated")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["qa"]["qa_status"] = "TECHNICAL_PASS"
    unapproved = tmp_path / "unapproved.json"
    unapproved.write_text(json.dumps(manifest), encoding="utf-8")
    exported = run_tool(
        str(ROOT / "tools" / "export_asset.py"),
        str(unapproved),
        "--profile",
        "generic_png",
        "--out",
        str(tmp_path / "blocked"),
    )
    assert exported.returncode != 0
    assert "allow-unapproved" in exported.stderr
