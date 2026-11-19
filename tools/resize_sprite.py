#!/usr/bin/env python
"""Resize a sprite with nearest-neighbour (pixel art) or high-quality resampling."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sprite_studio.cli import print_result, run
from sprite_studio.image_utils import (
    fit_canvas,
    integer_scale,
    load_image,
    pad_to_canvas,
    resize_rgba,
    resize_to_fit,
    save_png,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input")
    parser.add_argument("output")
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    parser.add_argument("--scale", type=int, help="Integer nearest-neighbour scale factor")
    parser.add_argument("--method", choices=["nearest", "box", "bilinear", "bicubic", "lanczos"], default="nearest")
    parser.add_argument("--fit", action="store_true", help="Preserve aspect ratio inside width/height, then pad")
    parser.add_argument("--anchor", default="center", help="Anchor when padding")
    parser.add_argument("--no-upscale", action="store_true", help="Do not enlarge when using --fit")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    image = load_image(args.input)
    original = image.size
    if args.scale:
        if args.width or args.height:
            parser.error("--scale cannot be combined with --width/--height")
        result = integer_scale(image, args.scale)
    elif args.width and args.height:
        if args.fit:
            result = resize_to_fit(
                image,
                args.width,
                args.height,
                args.method,
                allow_upscale=not args.no_upscale,
            )
            result = pad_to_canvas(result, args.width, args.height, args.anchor)
        else:
            result = resize_rgba(image, args.width, args.height, args.method)
    else:
        parser.error("Provide --width and --height, or --scale")
    out = save_png(result, args.output, overwrite=args.overwrite)
    report = {
        "input": args.input,
        "output": str(out),
        "original_size": list(original),
        "output_size": list(result.size),
        "method": args.method if not args.scale else "nearest",
        "scale": args.scale,
        "aspect_ratio_preserved": abs((result.width / result.height) - (original[0] / original[1])) < 0.001,
    }
    if args.json:
        print_result(report, as_json=True)
    else:
        print(f"{args.input} {original[0]}x{original[1]} -> {out} {result.width}x{result.height} ({report['method']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(run(main))
