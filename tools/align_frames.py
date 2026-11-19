#!/usr/bin/env python
"""Align animation frames to a shared canvas and pivot."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sprite_studio.animation import align_frames
from sprite_studio.cli import print_result, run
from sprite_studio.image_utils import load_image, save_png, write_json
from sprite_studio.sheets import find_frames


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("frames", help="Directory of PNG frames (or a single frame)")
    parser.add_argument("out_dir", help="Output directory for aligned frames")
    parser.add_argument("--canvas-width", type=int)
    parser.add_argument("--canvas-height", type=int)
    parser.add_argument("--pivot-x", type=int)
    parser.add_argument("--pivot-y", type=int)
    parser.add_argument("--align", choices=["bottom-center", "center", "none"], default="bottom-center")
    parser.add_argument("--no-align-y", action="store_true", help="Keep authored vertical movement (jump/fall)")
    parser.add_argument("--scale-mode", choices=["none", "fit_height", "match_first"], default="none")
    parser.add_argument("--target-height", type=int)
    parser.add_argument("--resample", choices=["nearest", "box", "bilinear", "bicubic", "lanczos"], default="nearest")
    parser.add_argument("--allow-clip", action="store_true")
    parser.add_argument("--prefix", default="frame", help="Output filename prefix")
    parser.add_argument("--report")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    source = Path(args.frames)
    paths = [source] if source.is_file() else find_frames(source)
    if not paths:
        raise ValueError(f"No PNG/WebP frames found in {source}")
    frames = [load_image(p) for p in paths]
    aligned, report = align_frames(
        frames,
        canvas_width=args.canvas_width,
        canvas_height=args.canvas_height,
        pivot_x=args.pivot_x,
        pivot_y=args.pivot_y,
        align=args.align,
        align_y=not args.no_align_y,
        scale_mode=args.scale_mode,
        target_height=args.target_height,
        resample=args.resample,
        allow_clip=args.allow_clip,
    )
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for i, frame in enumerate(aligned):
        path = out_dir / f"{args.prefix}__frame_{i:03d}.png"
        save_png(frame, path, overwrite=args.overwrite)
        written.append(str(path))
    report["outputs"] = written
    report["source_frames"] = [str(p) for p in paths]
    if args.report:
        write_json(args.report, report)
    if args.json:
        print_result(report, as_json=True)
    else:
        print(f"Aligned {len(aligned)} frames into {out_dir}")
        print(f"  canvas {report['canvas']['width']}x{report['canvas']['height']}  pivot ({report['pivot']['x']}, {report['pivot']['y']})")
        if report["clip_warnings"]:
            print(f"  WARNING: clipped frames {report['clip_warnings']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run(main))
