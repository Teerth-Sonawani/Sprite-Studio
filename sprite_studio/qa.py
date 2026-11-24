"""Technical QA and auditable visual-review records.

Technical checks never produce APPROVED on their own.  A separate visual review
must be recorded.  Human approval is tracked independently from an AI/agent
review so a manifest cannot accidentally imply human sign-off.
"""

from __future__ import annotations

import re
from pathlib import Path

from .image_utils import alpha_bbox, alpha_stats, image_info, load_image, palette, sha256_file, write_json
from .timeutil import utcnow as _utcnow

STATUSES = ["PENDING", "TECHNICAL_PASS", "VISUAL_REVIEW", "APPROVED", "REJECTED"]


def validate_sprite(path: str | Path, spec: dict | None = None, project_root: str | Path | None = None) -> dict:
    """Run deterministic technical checks and return a QA report.

    The result can be `TECHNICAL_PASS` or `REJECTED`.  It is never `APPROVED`;
    approval requires a visual review record.
    """

    spec = dict(spec or {})
    path = Path(path)
    checks: list[dict] = []

    def add(name: str, ok: bool, severity: str, detail: str, value=None):
        checks.append({"name": name, "ok": bool(ok), "severity": severity, "detail": detail, "value": value})

    if not path.is_file():
        return {
            "asset": str(path),
            "generated_at": _utcnow(),
            "technical_status": "REJECTED",
            "visual_status": "NOT_REVIEWED",
            "qa_status": "REJECTED",
            "checks": [{"name": "file_integrity", "ok": False, "severity": "critical", "detail": "file not found"}],
            "critical_failures": ["file_integrity"],
            "warnings": [],
            "human_approved": False,
        }

    try:
        image = load_image(path, None)
        rgba = image.convert("RGBA")
        info = image_info(path, include_palette=False)
        add("file_integrity", True, "critical", "image decoded successfully", info["format"])
    except Exception as exc:
        return {
            "asset": str(path),
            "generated_at": _utcnow(),
            "technical_status": "REJECTED",
            "visual_status": "NOT_REVIEWED",
            "qa_status": "REJECTED",
            "checks": [{"name": "file_integrity", "ok": False, "severity": "critical", "detail": str(exc)}],
            "critical_failures": ["file_integrity"],
            "warnings": [],
            "human_approved": False,
        }

    expected_w = spec.get("width") or spec.get("expected_width")
    expected_h = spec.get("height") or spec.get("expected_height")
    if expected_w is not None or expected_h is not None:
        dims_ok = (expected_w is None or image.width == int(expected_w)) and (expected_h is None or image.height == int(expected_h))
        add(
            "dimensions",
            dims_ok,
            "critical",
            f"{image.width}x{image.height}; expected {expected_w or '*'}x{expected_h or '*'}",
            [image.width, image.height],
        )
    else:
        add("dimensions", True, "info", f"{image.width}x{image.height}", [image.width, image.height])

    expected_mode = spec.get("mode") or spec.get("colour_mode")
    if expected_mode:
        mode_ok = image.mode.upper() == str(expected_mode).upper()
        add("colour_mode", mode_ok, "critical", f"mode={image.mode}, expected={expected_mode}", image.mode)
    else:
        add("colour_mode", True, "info", f"mode={image.mode}", image.mode)

    stats = alpha_stats(rgba)
    bbox = alpha_bbox(rgba)
    add("not_empty", bbox is not None, "critical", "visible content present" if bbox else "image is empty (all alpha=0)", stats["coverage"])
    if spec.get("transparency_required"):
        has_alpha = image.mode in {"RGBA", "LA"} or (image.mode == "P" and "transparency" in image.info)
        add("transparency", has_alpha and stats["transparent_pixels"] > 0, "critical", f"transparent pixels={stats['transparent_pixels']}", stats["transparent_pixels"])
    else:
        add("transparency", True, "info", f"transparent pixels={stats['transparent_pixels']}", stats["transparent_pixels"])

    min_cov = spec.get("min_coverage")
    max_cov = spec.get("max_coverage")
    cov = stats["coverage"]
    if min_cov is not None:
        add("min_coverage", cov >= float(min_cov), "warning", f"coverage {cov:.3f} >= {min_cov}", cov)
    if max_cov is not None:
        add("max_coverage", cov <= float(max_cov), "warning", f"coverage {cov:.3f} <= {max_cov}", cov)

    min_padding = int(spec.get("padding", 0) or 0)
    if bbox:
        pad_left, pad_top = bbox[0], bbox[1]
        pad_right, pad_bottom = image.width - 1 - bbox[2], image.height - 1 - bbox[3]
        actual_min = min(pad_left, pad_top, pad_right, pad_bottom)
        add(
            "padding",
            actual_min >= min_padding,
            "critical" if spec.get("padding_required") else "warning",
            f"min transparent padding {actual_min}px; required {min_padding}px",
            {"left": pad_left, "top": pad_top, "right": pad_right, "bottom": pad_bottom},
        )
        if not spec.get("allow_edge_contact", False):
            touches = actual_min == 0
            add("cropping", not touches, "critical", "content touches canvas edge" if touches else "content is inside the canvas", actual_min)
    else:
        add("padding", False, "critical", "no visible content", None)

    pivot = spec.get("pivot")
    if pivot:
        try:
            px, py = float(pivot["x"]), float(pivot["y"])
            ok = 0 <= px <= image.width and 0 <= py <= image.height
            add("pivot", ok, "critical", f"pivot ({px}, {py}) within {image.width}x{image.height}", [px, py])
        except Exception as exc:
            add("pivot", False, "critical", f"invalid pivot: {exc}", pivot)

    naming = spec.get("naming_pattern")
    if naming:
        ok = re.fullmatch(naming, path.name) is not None
        add("file_naming", ok, "warning", f"{path.name} against {naming}", path.name)

    palette_limit = spec.get("palette_limit") or spec.get("max_colours") or spec.get("max_colors")
    if palette_limit:
        colors = palette(rgba, max_colors=int(palette_limit) + 1)
        ok = len(colors) <= int(palette_limit)
        add("palette_limit", ok, "warning", f"{len(colors)} dominant colours; limit {palette_limit}", len(colors))

    max_file_mb = spec.get("max_file_mb")
    if max_file_mb:
        size_mb = path.stat().st_size / (1024 * 1024)
        add("file_size", size_mb <= float(max_file_mb), "warning", f"{size_mb:.2f} MB <= {max_file_mb} MB", size_mb)

    critical_failures = [c["name"] for c in checks if not c["ok"] and c["severity"] == "critical"]
    warnings = [c["name"] for c in checks if not c["ok"] and c["severity"] == "warning"]
    technical_status = "REJECTED" if critical_failures else "TECHNICAL_PASS"
    return {
        "asset": str(path),
        "generated_at": _utcnow(),
        "technical_status": technical_status,
        "visual_status": "NOT_REVIEWED",
        "qa_status": technical_status,
        "checks": checks,
        "critical_failures": critical_failures,
        "warnings": warnings,
        "stats": stats,
        "sha256": sha256_file(path),
        "spec": spec,
        "human_approved": False,
        "human_approved_at": None,
    }


def _check_evidence(evidence: list[str], evidence_root: str | Path | None) -> None:
    """Refuse to record evidence paths that do not exist.

    Approval without a real preview is the one failure this project exists to
    prevent, so a missing evidence file is an error, not a warning.
    """

    root = Path(evidence_root) if evidence_root is not None else Path.cwd()
    missing = []
    for item in evidence:
        path = Path(item)
        candidates = [path] if path.is_absolute() else [root / path, Path.cwd() / path]
        if not any(candidate.is_file() for candidate in candidates):
            missing.append(item)
    if missing:
        raise FileNotFoundError(
            "Review evidence does not exist: " + ", ".join(missing) +
            ". Create the contact sheet/preview first, or correct the paths."
        )


def record_visual_review(
    technical_report: dict,
    decision: str,
    reviewer: str,
    reviewer_type: str = "ai_agent",
    notes: str = "",
    scores: dict | None = None,
    evidence: list[str] | None = None,
    evidence_root: str | Path | None = None,
) -> dict:
    """Append a visual review to a technical report.

    decision: approve / revise / reject
    reviewer_type: ai_agent / human

    `evidence` must name files that exist; pass `evidence_root` when the paths
    are relative to a project or repository root rather than the working
    directory.
    """

    decision = decision.lower()
    if decision not in {"approve", "revise", "reject"}:
        raise ValueError("decision must be approve, revise or reject")
    technical_status = technical_report.get("technical_status") or technical_report.get("qa_status")
    if decision == "approve" and technical_status not in {"TECHNICAL_PASS", "APPROVED"}:
        raise ValueError("Cannot approve an asset that has not passed technical validation")
    evidence = list(evidence or [])
    if decision == "approve" and not evidence:
        raise ValueError("Approval requires at least one evidence path (contact sheet or preview)")
    _check_evidence(evidence, evidence_root)

    if decision == "approve":
        visual_status = "APPROVED"
        qa_status = "APPROVED"
    elif decision == "revise":
        visual_status = "VISUAL_REVIEW"
        qa_status = "VISUAL_REVIEW"
    else:
        visual_status = "REJECTED"
        qa_status = "REJECTED"

    report = dict(technical_report)
    report["visual_status"] = visual_status
    report["qa_status"] = qa_status
    report["review"] = {
        "decision": decision,
        "reviewer": reviewer,
        "reviewer_type": reviewer_type,
        "reviewed_at": _utcnow(),
        "notes": notes,
        "scores": scores or {},
        "evidence": evidence or [],
        "human_approved": reviewer_type == "human" and decision == "approve",
        "approval_scope": "production" if reviewer_type == "human" and decision == "approve" else "demo_or_internal",
    }
    report["human_approved"] = report["review"]["human_approved"]
    report["human_approved_at"] = report["review"]["reviewed_at"] if report["human_approved"] else None
    return report


def write_review(report: dict, path: str | Path) -> Path:
    return write_json(path, report)


# Blocking severity, worst first.  This is a release-gate ladder, not a quality
# ladder: a REJECTED asset is a hard stop, a PENDING asset has never been
# validated (so nothing is known), VISUAL_REVIEW means known defects are being
# corrected, TECHNICAL_PASS has passed deterministic checks but no human or
# agent has looked at it, and APPROVED is releasable within its approval scope.
STATUS_SEVERITY = {
    "REJECTED": 4,
    "PENDING": 3,
    "VISUAL_REVIEW": 2,
    "TECHNICAL_PASS": 1,
    "APPROVED": 0,
}


def worst_status(*statuses: str) -> str:
    """Return the most blocking status.

    With no arguments the result is `PENDING`: nothing has been validated yet.
    """

    if not statuses:
        return "PENDING"
    for status in statuses:
        if status not in STATUS_SEVERITY:
            raise ValueError(f"Unknown status {status!r}")
    return max(statuses, key=lambda s: STATUS_SEVERITY[s])
