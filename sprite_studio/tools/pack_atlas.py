#!/usr/bin/env python
"""Pack PNG frames into a texture atlas with JSON frame metadata."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sprite_studio.atlas import pack_files
from sprite_studio.cli import print_result, run
from sprite_studio.image_utils import natural_key
from sprite_studio.sheets import find_frames


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("frames", nargs="+", help="Directory or frame files")
    parser.add_argument("--output", required=True)
    parser.add_argument("--metadata", required=True)
    parser.add_argument("--max-width", type=int, default=2048)
    parser.add_argument("--max-height", type=int, default=2048)
    parser.add_argument("--padding", type=int, default=2)
    parser.add_argument("--pot", action="store_true", help="Round atlas dimensions up to powers of two")
    parser.add_argument("--sort", choices=["height", "area", "name", "none"], default="height")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    paths: list[Path] = []
    for value in args.frames:
        # Semicolons are kept for backward compatibility with the earlier CLI.
        for part in value.split(";"):
            path = Path(part)
            paths.extend(find_frames(path) if path.is_dir() else [path])
    unique = {p.resolve(): p for p in paths}
    paths = sorted(unique.values(), key=lambda p: natural_key(p.name))
    if not paths:
        raise ValueError("No frames found")
    meta = pack_files(
        paths,
        args.output,
        metadata_path=args.metadata,
        overwrite=args.overwrite,
        max_width=args.max_width,
        max_height=args.max_height,
        padding=args.padding,
        power_of_two=args.pot,
        sort=args.sort,
    )
    if args.json:
        print_result(meta, as_json=True)
    else:
        print(f"Atlas -> {args.output} ({meta['image']['width']}x{meta['image']['height']}, {meta['frame_count']} frames)")
    return 0


def cli() -> None:
    """Console-script wrapper with consistent error handling and exit codes."""

    run(main)
