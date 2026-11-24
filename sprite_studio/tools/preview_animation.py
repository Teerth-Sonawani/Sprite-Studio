#!/usr/bin/env python
"""Build an animated preview (GIF, APNG, WebP or MP4) from PNG frames."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sprite_studio.animation import make_preview
from sprite_studio.cli import print_result, run
from sprite_studio.image_utils import load_image
from sprite_studio.sheets import find_frames


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("frames", help="Directory of frames or one frame file")
    parser.add_argument("--output", required=True, help=".gif, .png/.apng, .webp, .mp4 or .webm")
    parser.add_argument("--frames-per-second", type=float, default=10.0)
    parser.add_argument("--durations", help="Comma-separated durations in ms (overrides fps)")
    parser.add_argument("--once", action="store_true", help="Do not loop")
    parser.add_argument("--background", default="checker", help="checker, transparent or #RRGGBB")
    parser.add_argument("--size", help="WxH output size")
    parser.add_argument("--scale", type=int, default=1)
    parser.add_argument("--title")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    path = Path(args.frames)
    paths = find_frames(path) if path.is_dir() else [path]
    if not paths:
        raise ValueError(f"No frames found in {path}")
    frames = [load_image(p) for p in paths]
    durations = None
    if args.durations:
        durations = [int(v.strip()) for v in args.durations.split(",") if v.strip()]
    size = None
    if args.size:
        parts = args.size.lower().split("x")
        if len(parts) != 2:
            raise ValueError("--size must look like 128x128")
        size = (int(parts[0]), int(parts[1]))
    out = make_preview(
        frames,
        args.output,
        durations=durations,
        fps=args.frames_per_second,
        loop=not args.once,
        background=args.background,
        size=size,
        scale=args.scale,
        overwrite=args.overwrite,
        title=args.title,
    )
    result = {"output": str(out), "frames": len(frames), "loop": not args.once, "size": list(frames[0].size)}
    if args.json:
        print_result(result, as_json=True)
    else:
        print(f"Preview -> {out} ({len(frames)} frames, {'loop' if not args.once else 'once'})")
    return 0


def cli() -> None:
    """Console-script wrapper with consistent error handling and exit codes."""

    run(main)
