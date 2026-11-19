#!/usr/bin/env python
"""Create a labelled contact sheet for visual review."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sprite_studio.cli import print_result, run
from sprite_studio.image_utils import save_png
from sprite_studio.sheets import contact_sheet, find_frames


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("frames", nargs="+", help="Directory or frame files")
    parser.add_argument("--output", required=True)
    parser.add_argument("--columns", type=int, default=4)
    parser.add_argument("--thumb-width", type=int, default=128)
    parser.add_argument("--thumb-height", type=int, default=128)
    parser.add_argument("--background", default="checker", help="checker, transparent or #RRGGBB")
    parser.add_argument("--title")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    paths: list[Path] = []
    for value in args.frames:
        path = Path(value)
        if path.is_dir():
            paths.extend(find_frames(path))
        elif path.is_file():
            paths.append(path)
        else:
            raise FileNotFoundError(value)
    if not paths:
        raise ValueError("No frames found")
    if len(paths) == 1 and paths[0].is_dir():
        paths = find_frames(paths[0])
    labels = [p.name for p in paths]
    sheet = contact_sheet(
        paths,
        labels=labels,
        columns=args.columns,
        thumb_width=args.thumb_width,
        thumb_height=args.thumb_height,
        background=args.background,
        title=args.title,
    )
    out = save_png(sheet, args.output, overwrite=args.overwrite)
    result = {"output": str(out), "frames": len(paths), "columns": args.columns, "size": list(sheet.size)}
    if args.json:
        print_result(result, as_json=True)
    else:
        print(f"Contact sheet -> {out} ({sheet.width}x{sheet.height}, {len(paths)} frames)")
    return 0


if __name__ == "__main__":
    raise SystemExit(run(main))
