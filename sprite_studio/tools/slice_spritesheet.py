#!/usr/bin/env python
"""Slice a sprite sheet into frames using a declared grid."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sprite_studio.cli import print_result, run
from sprite_studio.image_utils import load_image, write_json
from sprite_studio.sheets import slice_sheet


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("image", help="Sprite sheet image")
    parser.add_argument("--columns", type=int)
    parser.add_argument("--rows", type=int)
    parser.add_argument("--cell-width", type=int)
    parser.add_argument("--cell-height", type=int)
    parser.add_argument("--margin", type=int, default=0)
    parser.add_argument("--spacing", type=int, default=0)
    parser.add_argument("--out-dir", default="frames")
    parser.add_argument("--prefix", default="frame")
    parser.add_argument("--keep-empty", action="store_true", help="Write empty cells instead of recording and skipping them")
    parser.add_argument("--metadata", help="Write layout metadata JSON")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    image = load_image(args.image)
    meta = slice_sheet(
        image,
        columns=args.columns,
        rows=args.rows,
        cell_width=args.cell_width,
        cell_height=args.cell_height,
        margin=args.margin,
        spacing=args.spacing,
        skip_empty=not args.keep_empty,
        prefix=args.prefix,
        out_dir=args.out_dir,
        overwrite=args.overwrite,
    )
    meta["source_file"] = str(Path(args.image).resolve())
    if args.metadata:
        write_json(args.metadata, meta)
    if args.json:
        print_result(meta, as_json=True)
    else:
        layout = meta["layout"]
        print(
            f"Sliced {args.image} into {meta['frame_count']} frames\n"
            f"  grid {layout['columns']}x{layout['rows']} cells {layout['cell_width']}x{layout['cell_height']}\n"
            f"  empty cells: {meta['empty_cell_count']}\n"
            f"  output: {args.out_dir}"
        )
    return 0


def cli() -> None:
    """Console-script wrapper with consistent error handling and exit codes."""

    run(main)
