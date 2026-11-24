#!/usr/bin/env python
"""Assemble PNG frames into a horizontal, vertical or grid sprite sheet."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sprite_studio.cli import print_result, run
from sprite_studio.image_utils import load_image, natural_key, parse_color, save_png, write_json
from sprite_studio.sheets import build_sheet, find_frames


def _paths(value: str) -> list[Path]:
    path = Path(value)
    if path.is_dir():
        return find_frames(path)
    if path.is_file():
        return [path]
    raise FileNotFoundError(value)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("frames", nargs="+", help="Frame directory or individual frame files")
    parser.add_argument("--output", required=True)
    parser.add_argument("--metadata")
    parser.add_argument("--layout", choices=["horizontal", "vertical", "grid"], default="horizontal")
    parser.add_argument("--columns", type=int)
    parser.add_argument("--rows", type=int)
    parser.add_argument("--cell-width", type=int)
    parser.add_argument("--cell-height", type=int)
    parser.add_argument("--spacing", type=int, default=0)
    parser.add_argument("--margin", type=int, default=0)
    parser.add_argument("--background", default="transparent", help="transparent or #RRGGBB")
    parser.add_argument("--durations", help="Comma-separated per-frame durations in ms")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    paths: list[Path] = []
    for value in args.frames:
        paths.extend(_paths(value))
    # Natural filename order keeps frame_2 before frame_10, and de-duplicates
    # paths that appear both directly and via their containing directory.
    unique = {p.resolve(): p for p in paths}
    paths = sorted(unique.values(), key=lambda p: natural_key(p.name))
    if not paths:
        raise ValueError("No frames found")
    frames = [load_image(p) for p in paths]
    bg = (0, 0, 0, 0) if args.background == "transparent" else parse_color(args.background)
    durations = None
    if args.durations:
        durations = [int(part.strip()) for part in args.durations.split(",") if part.strip()]
    sheet, meta = build_sheet(
        frames,
        layout=args.layout,
        columns=args.columns,
        rows=args.rows,
        cell_width=args.cell_width,
        cell_height=args.cell_height,
        spacing=args.spacing,
        margin=args.margin,
        background=bg,
        durations=durations,
        metadata={"source_frames": [str(p) for p in paths]},
    )
    out = save_png(sheet, args.output, overwrite=args.overwrite)
    meta["output"] = str(out)
    if args.metadata:
        write_json(args.metadata, meta)
    if args.json:
        print_result(meta, as_json=True)
    else:
        print(f"Built {out} ({sheet.width}x{sheet.height}) from {len(frames)} frames")
    return 0


def cli() -> None:
    """Console-script wrapper with consistent error handling and exit codes."""

    run(main)
