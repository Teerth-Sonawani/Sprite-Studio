#!/usr/bin/env python
"""Inspect an image: dimensions, mode, alpha coverage, bbox, palette and hash."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sprite_studio.cli import print_result, run
from sprite_studio.image_utils import image_info


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("image", help="Image file to inspect")
    parser.add_argument("--palette", action="store_true", help="Include dominant colours")
    parser.add_argument("--max-colors", type=int, default=16, help="Maximum palette colours (default 16)")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    parser.add_argument("--report", help="Write the report JSON to this path")
    args = parser.parse_args()

    info = image_info(args.image, include_palette=args.palette, max_colors=args.max_colors)
    if args.report:
        from sprite_studio.image_utils import write_json

        write_json(args.report, info)
    if args.json:
        print_result(info, as_json=True)
    else:
        alpha = info["alpha"]
        bbox = alpha["bbox"]
        lines = [
            f"{info['filename']}",
            f"  format: {info['format']}   mode: {info['mode']}   size: {info['width']}x{info['height']}",
            f"  frames: {info['n_frames']}   bytes: {info['file_size']:,}",
            f"  alpha coverage: {alpha['coverage']:.2%}   partial: {alpha['partial_pixels']}   bbox: {bbox}",
            f"  sha256: {info['sha256']}",
        ]
        if args.palette:
            lines.append("  palette:")
            for item in info["palette"]:
                lines.append(f"    {item['hex']}  {item['percent']:5.1f}%  ({item['pixels']} px)")
        print_result(info, as_json=False, human="\n".join(lines))
    return 0


def cli() -> None:
    """Console-script wrapper with consistent error handling and exit codes."""

    run(main)
