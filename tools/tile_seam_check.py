#!/usr/bin/env python
"""Check tile edge continuity and generate wrap/assembled previews."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sprite_studio.cli import print_result, run
from sprite_studio.image_utils import load_image, save_png, write_json
from sprite_studio.tiling import assembled_preview, seam_report, wrap_preview


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("image", help="Tile image")
    parser.add_argument("--threshold", type=float, default=2.0, help="Maximum seam/interior ratio (default 2.0)")
    parser.add_argument("--max-edge-diff", type=float, default=48.0, help="Absolute edge difference that still passes")
    parser.add_argument("--preview", help="Write a 2x2 wrap preview")
    parser.add_argument("--assembled", help="Write a 3x3 assembled preview with tile boundaries")
    parser.add_argument("--grid", type=int, default=3)
    parser.add_argument("--report")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    image = load_image(args.image)
    if image.width != image.height:
        print("NOTE: tile is not square; check the engine's tile size expectations.", file=sys.stderr)
    report = seam_report(image, threshold=args.threshold, max_edge_diff=args.max_edge_diff)
    report["image"] = args.image
    report["size"] = list(image.size)
    if args.preview:
        save_png(wrap_preview(image, 2), args.preview, overwrite=args.overwrite)
        report["wrap_preview"] = args.preview
    if args.assembled:
        save_png(assembled_preview(image, args.grid), args.assembled, overwrite=args.overwrite)
        report["assembled_preview"] = args.assembled
    if args.report:
        write_json(args.report, report)
    if args.json:
        print_result(report, as_json=True)
    else:
        print(f"{args.image} ({image.width}x{image.height}): {report['status']}")
        for axis, values in report["axes"].items():
            print(
                f"  {axis}: edge {values['edge_mean_abs_diff']}  interior {values['interior_mean_abs_diff']}  "
                f"ratio {values['seam_ratio']} -> {'PASS' if values['passes_ratio'] or values['passes_absolute'] else 'WARN'}"
            )
        print("  " + report["note"])
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(run(main))
