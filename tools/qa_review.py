#!/usr/bin/env python
"""Record a visual review. Approval requires technical pass and evidence."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sprite_studio.cli import print_result, run
from sprite_studio.image_utils import read_json, write_json
from sprite_studio.qa import record_visual_review


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("report", help="Technical QA report JSON from validate_sprite.py")
    parser.add_argument("--decision", required=True, choices=["approve", "revise", "reject"])
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--reviewer-type", choices=["ai_agent", "human"], default="ai_agent")
    parser.add_argument("--notes", default="")
    parser.add_argument("--score", action="append", help="criterion=0-5; repeatable")
    parser.add_argument("--evidence", action="append", help="Path to preview/contact sheet; required to approve")
    parser.add_argument("--output", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    technical = read_json(args.report)
    scores = {}
    for item in args.score or []:
        if "=" not in item:
            raise ValueError("--score must be criterion=value")
        key, value = item.split("=", 1)
        scores[key] = float(value)
    review = record_visual_review(
        technical,
        decision=args.decision,
        reviewer=args.reviewer,
        reviewer_type=args.reviewer_type,
        notes=args.notes,
        scores=scores,
        evidence=args.evidence or [],
    )
    write_json(args.output, review)
    if args.json:
        print_result(review, as_json=True)
    else:
        print(f"Review -> {args.output}")
        print(f"  decision: {review['review']['decision']}   qa: {review['qa_status']}   human-approved: {review['human_approved']}")
        if review.get("human_approved") is False and args.decision == "approve":
            print("  NOTE: approved for demo/internal use only; a human must sign off before production release.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run(main))
