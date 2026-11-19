#!/usr/bin/env python
"""Remove tiny alpha islands, optionally fill enclosed holes, and report every change."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sprite_studio.background import clean_transparency
from sprite_studio.cli import print_result, run
from sprite_studio.image_utils import load_image, save_png, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input")
    parser.add_argument("output")
    parser.add_argument("--min-island", type=int, default=4, help="Remove visible components smaller than this many pixels (default 4)")
    parser.add_argument("--alpha-floor", type=int, default=0, help="Set alpha at or below this value to 0")
    parser.add_argument("--fill-holes", action="store_true", help="Fill transparent regions enclosed by the subject")
    parser.add_argument("--no-preserve-largest", action="store_true", help="Allow the largest component to be removed if below min-island")
    parser.add_argument("--smooth", type=int, default=0, help="Blur alpha by this radius (use sparingly)")
    parser.add_argument("--report")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    image = load_image(args.input)
    result, report = clean_transparency(
        image,
        min_island=args.min_island,
        alpha_floor=args.alpha_floor,
        fill_holes=args.fill_holes,
        preserve_largest=not args.no_preserve_largest,
        smooth=args.smooth,
    )
    out = save_png(result, args.output, overwrite=args.overwrite)
    report["output"] = str(out)
    if args.report:
        write_json(args.report, report)
    if args.json:
        print_result(report, as_json=True)
    else:
        print(
            f"{args.input} -> {out}\n"
            f"  removed components: {report['removed_component_count']} ({report['removed_pixels']} px)\n"
            f"  filled holes: {report['filled_hole_pixels']} px\n"
            f"  visible pixels: {report['remaining_visible_pixels']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(run(main))
