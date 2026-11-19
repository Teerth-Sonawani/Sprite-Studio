"""Technical QA, visual-review and manifest tests."""

from __future__ import annotations

import json

import pytest
from PIL import Image

from sprite_studio.image_utils import save_png
from sprite_studio.manifest import validate_manifest
from sprite_studio.qa import record_visual_review, validate_sprite, worst_status

SPEC = {
    "width": 16,
    "height": 16,
    "mode": "RGBA",
    "transparency_required": True,
    "padding": 2,
    "pivot": {"x": 8, "y": 15},
}


def test_validate_sprite_passes_valid_fixture(tmp_path, frame):
    path = tmp_path / "frame.png"
    save_png(frame, path)
    report = validate_sprite(path, SPEC)
    assert report["technical_status"] == "TECHNICAL_PASS"
    assert report["qa_status"] == "TECHNICAL_PASS"
    assert report["visual_status"] == "NOT_REVIEWED"
    assert report["human_approved"] is False
    assert report["critical_failures"] == []


def test_validate_sprite_rejects_wrong_dimensions_and_missing_file(tmp_path, frame):
    path = tmp_path / "frame.png"
    save_png(frame, path)
    report = validate_sprite(path, {**SPEC, "width": 32})
    assert report["technical_status"] == "REJECTED"
    assert "dimensions" in report["critical_failures"]

    missing = validate_sprite(tmp_path / "missing.png", SPEC)
    assert missing["technical_status"] == "REJECTED"
    assert "file_integrity" in missing["critical_failures"]


def test_validate_sprite_rejects_edge_contact(tmp_path):
    image = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    image.paste((80, 140, 90, 255), (0, 0, 16, 16))
    path = tmp_path / "full.png"
    save_png(image, path)
    report = validate_sprite(path, SPEC)
    assert report["technical_status"] == "REJECTED"
    assert "cropping" in report["critical_failures"]


def test_visual_review_requires_evidence_and_technical_pass(tmp_path, frame):
    path = tmp_path / "frame.png"
    save_png(frame, path)
    technical = validate_sprite(path, SPEC)
    with pytest.raises(ValueError):
        record_visual_review(technical, "approve", "reviewer", evidence=[])
    rejected = {**technical, "technical_status": "REJECTED", "qa_status": "REJECTED"}
    with pytest.raises(ValueError):
        record_visual_review(rejected, "approve", "reviewer", evidence=["evidence.png"])


def test_ai_review_is_demo_scoped_and_human_review_is_production(tmp_path, frame):
    path = tmp_path / "frame.png"
    save_png(frame, path)
    technical = validate_sprite(path, SPEC)
    ai = record_visual_review(technical, "approve", "agent", reviewer_type="ai_agent", evidence=["contact.png"])
    assert ai["qa_status"] == "APPROVED"
    assert ai["human_approved"] is False
    assert ai["human_approved_at"] is None
    assert ai["review"]["approval_scope"] == "demo_or_internal"

    human = record_visual_review(technical, "approve", "artist", reviewer_type="human", evidence=["contact.png"])
    assert human["qa_status"] == "APPROVED"
    assert human["human_approved"] is True
    assert human["review"]["approval_scope"] == "production"


def test_revise_and_reject_decisions():
    technical = {"technical_status": "TECHNICAL_PASS", "qa_status": "TECHNICAL_PASS"}
    revise = record_visual_review(technical, "revise", "agent", notes="Fix the eye")
    assert revise["qa_status"] == "VISUAL_REVIEW"
    reject = record_visual_review(technical, "reject", "agent", notes="Wrong subject")
    assert reject["qa_status"] == "REJECTED"


def test_bad_decision_and_status_combination():
    technical = {"technical_status": "TECHNICAL_PASS", "qa_status": "TECHNICAL_PASS"}
    with pytest.raises(ValueError):
        record_visual_review(technical, "maybe", "agent")
    assert worst_status("TECHNICAL_PASS", "APPROVED") == "TECHNICAL_PASS"
    assert worst_status("REJECTED", "APPROVED") == "REJECTED"
    with pytest.raises(ValueError):
        worst_status("UNKNOWN")


def test_manifest_paths_reviews_and_schema(demo_asset, root):
    manifest = demo_asset["manifest"]
    assert manifest["asset_id"] == "demo"
    assert manifest["qa"]["qa_status"] == "APPROVED"
    assert manifest["qa"]["human_approved"] is False
    assert manifest["qa"]["report"] == "../qa/demo_review.json"
    assert manifest["asset_root"] == "../assets/approved/demo"
    assert manifest["animations"]["idle"]["frame_count"] == 2
    assert manifest["files"]["sheet_metadata"]

    roles = manifest["files"]
    assert roles["frame"] and roles["frame"][0]["path"].startswith("../assets/approved/demo/frames/")
    preview_names = {record["filename"] for record in roles["preview"]}
    assert "demo__idle__preview.gif" in preview_names

    ok, errors = validate_manifest(manifest, root / "schemas" / "asset_manifest.schema.json")
    assert ok, errors
    assert json.loads(demo_asset["manifest_path"].read_text(encoding="utf-8"))["asset_id"] == "demo"


def test_manifest_rejects_approval_without_technical_pass(demo_asset, root):
    manifest = json.loads(json.dumps(demo_asset["manifest"]))
    manifest["qa"]["technical_status"] = "PENDING"
    ok, errors = validate_manifest(manifest, root / "schemas" / "asset_manifest.schema.json")
    assert not ok
    assert any("technical pass" in error for error in errors)
