#!/usr/bin/env python
"""Report, compare and optionally quantize a sprite palette."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sprite_studio.cli import print_result, run
from sprite_studio.image_utils import color_distance, color_hex, load_image, palette, parse_color, save_png, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("image")
    parser.add_argument("--max-colors", type=int, default=24, help="Maximum colours to extract")
    parser.add_argument("--limit", type=int, help="Fail if the visible palette exceeds this count")
    parser.add_argument("--compare", help="Comma-separated hex list or a text/YAML file of hex colours")
    parser.add_argument("--max-distance", type=float, default=42.0, help="Maximum nearest-colour distance")
    parser.add_argument("--quantize", help="Write a colour-reduced PNG (palette limit required)")
    parser.add_argument("--report")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    image = load_image(args.image)
    colors = palette(image, max_colors=args.max_colors)
    report = {
        "image": args.image,
        "size": list(image.size),
        "visible_colours": len(colors),
        "palette": colors,
        "limit": args.limit,
        "within_limit": len(colors) <= args.limit if args.limit else None,
    }
    if args.compare:
        compare_path = Path(args.compare)
        if compare_path.is_file():
            text = compare_path.read_text(encoding="utf-8")
            tokens = [t.strip() for t in text.replace("[", "").replace("]", "").replace(",", " ").split()]
        else:
            tokens = [t.strip() for t in args.compare.split(",")]
        target = [parse_color(t)[:3] for t in tokens if t]
        matches = []
        worst = 0.0
        for color in colors:
            best = min(((color_distance(color["rgb"], t), color_hex(t)) for t in target), default=(999, None))
            worst = max(worst, best[0])
            matches.append({"colour": color["hex"], "nearest_target": best[1], "distance": round(best[0], 2)})
        report["comparison"] = {
            "target_colours": [color_hex(t) for t in target],
            "matches": matches,
            "worst_distance": round(worst, 2),
            "within_max_distance": worst <= args.max_distance,
        }
    if args.quantize:
        if not args.limit:
            raise ValueError("--quantize requires --limit")
        # Quantize visible RGB, then restore the original alpha channel.
        rgb = image.convert("RGB").quantize(colors=args.limit, method=2).convert("RGBA")
        rgb.putalpha(image.getchannel("A"))
        out = save_png(rgb, args.quantize, overwrite=args.overwrite)
        report["quantized_output"] = str(out)
    if args.report:
        write_json(args.report, report)
    if args.json:
        print_result(report, as_json=True)
    else:
        print(f"{args.image}: {len(colors)} visible colours")
        for color in colors:
            print(f"  {color['hex']}  {color['percent']:5.1f}%  {color['pixels']} px")
        if report["within_limit"] is False:
            print(f"  FAIL: exceeds limit of {args.limit}")
        if args.compare:
            comp = report["comparison"]
            print(f"  comparison: worst distance {comp['worst_distance']} -> {'PASS' if comp['within_max_distance'] else 'FAIL'}")
    if report["within_limit"] is False:
        return 1
    if args.compare and not report["comparison"]["within_max_distance"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(run(main))
