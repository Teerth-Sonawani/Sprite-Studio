#!/usr/bin/env python
"""Validate frame count, canvas, placement, scale, palette drift and loop seam."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sprite_studio.animation import validate_animation
from sprite_studio.cli import print_result, run
from sprite_studio.image_utils import load_image, write_json
from sprite_studio.sheets import find_frames


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("frames", help="Directory of frames or one frame")
    parser.add_argument("--expected-count", type=int)
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    parser.add_argument("--pivot-x", type=int)
    parser.add_argument("--pivot-y", type=int)
    parser.add_argument("--once", action="store_true", help="Animation is not looping")
    parser.add_argument("--durations", help="Comma-separated durations in ms")
    parser.add_argument("--max-displacement", type=float, default=12.0)
    parser.add_argument("--max-scale-variation", type=float, default=0.22)
    parser.add_argument("--max-palette-drift", type=float, default=28.0)
    parser.add_argument("--max-loop-diff", type=float, default=42.0)
    parser.add_argument("--border-tolerance", type=float, default=0.01)
    parser.add_argument("--report")
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
    pivot = (args.pivot_x, args.pivot_y) if args.pivot_x is not None and args.pivot_y is not None else None
    size = (args.width, args.height) if args.width and args.height else None
    report = validate_animation(
        frames,
        expected_count=args.expected_count,
        expected_size=size,
        pivot=pivot,
        loop=not args.once,
        durations=durations,
        max_displacement=args.max_displacement,
        max_scale_variation=args.max_scale_variation,
        max_palette_drift=args.max_palette_drift,
        max_loop_diff=args.max_loop_diff,
        border_tolerance=args.border_tolerance,
    )
    report["source_frames"] = [str(p) for p in paths]
    if args.report:
        write_json(args.report, report)
    if args.json:
        print_result(report, as_json=True)
    else:
        print(f"Animation validation: {report['status']} ({report['frames']} frames)")
        for check in report["checks"]:
            mark = "OK  " if check["ok"] else ("FAIL" if check["severity"] == "critical" else "WARN")
            print(f"  [{mark}] {check['name']}: {check['detail']}")
    return 0 if report["status"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(run(main))
