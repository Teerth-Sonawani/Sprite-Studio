#!/usr/bin/env python
"""Technical sprite validation. Never marks an asset APPROVED; visual review is separate."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sprite_studio.cli import print_result, run
from sprite_studio.image_utils import write_json
from sprite_studio.manifest import _load_structured
from sprite_studio.qa import validate_sprite


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("image", help="Sprite/image to validate")
    parser.add_argument("--spec", help="YAML/JSON specification with width, height, padding, pivot, etc.")
    parser.add_argument("--width", type=int, help="Expected width")
    parser.add_argument("--height", type=int, help="Expected height")
    parser.add_argument("--mode", help="Expected Pillow mode, e.g. RGBA")
    parser.add_argument("--transparency", action="store_true", help="Require transparency")
    parser.add_argument("--padding", type=int, default=0, help="Minimum transparent padding (px)")
    parser.add_argument("--pivot-x", type=float)
    parser.add_argument("--pivot-y", type=float)
    parser.add_argument("--naming", help="Python regex the file name must match")
    parser.add_argument("--palette-limit", type=int)
    parser.add_argument("--min-coverage", type=float)
    parser.add_argument("--max-coverage", type=float)
    parser.add_argument("--allow-edge-contact", action="store_true")
    parser.add_argument("--report", help="Write QA report JSON")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    spec = _load_structured(args.spec) if args.spec else {}
    for key in ("width", "height", "mode", "min_coverage", "max_coverage", "palette_limit", "naming_pattern"):
        value = getattr(args, key, None)
        if value is not None:
            spec[key] = value
    if args.transparency:
        spec["transparency_required"] = True
    if args.padding:
        spec["padding"] = args.padding
    if args.pivot_x is not None or args.pivot_y is not None:
        spec["pivot"] = {"x": args.pivot_x or 0, "y": args.pivot_y or 0}
    if args.allow_edge_contact:
        spec["allow_edge_contact"] = True

    report = validate_sprite(args.image, spec)
    if args.report:
        write_json(args.report, report)
    if args.json:
        print_result(report, as_json=True)
    else:
        lines = [
            f"{report['asset']}",
            f"  technical: {report['technical_status']}   visual: {report['visual_status']}   qa: {report['qa_status']}",
        ]
        for check in report["checks"]:
            mark = "OK  " if check["ok"] else ("FAIL" if check["severity"] == "critical" else "WARN")
            lines.append(f"  [{mark}] {check['name']}: {check['detail']}")
        if report.get("critical_failures"):
            lines.append("  critical failures: " + ", ".join(report["critical_failures"]))
        print_result(report, as_json=False, human="\n".join(lines))
    return 0 if report["technical_status"] == "TECHNICAL_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(run(main))
