#!/usr/bin/env python
"""Remove a backdrop with edge-connected flood fill, then save an RGBA PNG."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sprite_studio.background import remove_background
from sprite_studio.cli import print_result, run
from sprite_studio.image_utils import load_image, save_png, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", help="Source image")
    parser.add_argument("output", help="Output RGBA PNG")
    parser.add_argument("--tolerance", type=int, default=28, help="RGB distance tolerance (default 28)")
    parser.add_argument("--border", type=int, default=2, help="Border sample width (default 2)")
    parser.add_argument("--method", choices=["edge", "global", "none"], default="edge", help="Removal strategy")
    parser.add_argument("--colour", action="append", help="Explicit background colour (#RRGGBB); repeatable")
    parser.add_argument("--feather", type=int, default=0, help="Soften the cut edge by this blur radius")
    parser.add_argument("--alpha-floor", type=int, default=0, help="Zero alpha at or below this value")
    parser.add_argument("--mask-preview", help="Save a black/white removal-mask preview")
    parser.add_argument("--report", help="Write a processing report JSON")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    image = load_image(args.input)
    colours = None
    if args.colour:
        from sprite_studio.image_utils import parse_color

        colours = [parse_color(c)[:3] for c in args.colour]
    result, report = remove_background(
        image,
        tolerance=args.tolerance,
        border=args.border,
        method=args.method,
        colors=colours,
        feather=args.feather,
        alpha_floor=args.alpha_floor,
    )
    out = save_png(result, args.output, overwrite=args.overwrite)
    report["output"] = str(out)
    if args.mask_preview:
        alpha = result.getchannel("A")
        preview = Image.merge("RGBA", (alpha, alpha, alpha, Image.new("L", result.size, 255)))
        save_png(preview, args.mask_preview, overwrite=args.overwrite)
        report["mask_preview"] = args.mask_preview
    if args.report:
        write_json(args.report, report)
    if args.json:
        print_result(report, as_json=True)
    else:
        print(
            f"{args.input} -> {out}\n"
            f"  removed {report['removed_pixels']} px; visible {report['remaining_visible_pixels']} px\n"
            f"  border residual: {report['border_residual_percent']}%\n"
            + (f"  WARNING: {report['warning']}" if report.get("warning") else "  no border residual warning")
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(run(main))
