#!/usr/bin/env python
"""Import a manually generated image and record provenance.

Use this after the manual Perchance handoff (or any out-of-band generation) so
the source file, hash, prompt and model label stay attached to the asset.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from sprite_studio.cli import print_result, run
from sprite_studio.image_utils import image_info, write_json
from sprite_studio.timeutil import utcnow as _utcnow


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("image", help="Downloaded/generated image")
    parser.add_argument("--dest", required=True, help="Destination file or source directory")
    parser.add_argument("--asset-id", required=True)
    parser.add_argument("--provider", default="perchance")
    parser.add_argument("--mode", default="manual")
    parser.add_argument("--model", default="")
    parser.add_argument("--generation-id", default="")
    parser.add_argument("--prompt-file")
    parser.add_argument("--notes", default="")
    parser.add_argument(
        "--terms-confirmed",
        action="store_true",
        help="You have read the provider's terms and licence for this image. Recorded as provenance.",
    )
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    src = Path(args.image)
    if not src.is_file():
        raise FileNotFoundError(args.image)
    info = image_info(src, include_palette=False)
    dest = Path(args.dest)
    if dest.is_dir() or not dest.suffix:
        dest.mkdir(parents=True, exist_ok=True)
        dest = dest / f"{args.asset_id}__source{src.suffix.lower()}"
    if dest.exists() and not args.overwrite:
        raise FileExistsError(f"Refusing to overwrite {dest}. Pass --overwrite.")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    prompt = None
    if args.prompt_file:
        prompt = Path(args.prompt_file).read_text(encoding="utf-8")
    provenance = {
        "asset_id": args.asset_id,
        "imported_at": _utcnow(),
        "original_path": str(src.resolve()),
        "stored_path": str(dest.resolve()),
        "provider": args.provider,
        "mode": args.mode,
        "model_key": args.model or None,
        "generation_id": args.generation_id or None,
        "prompt": prompt,
        "prompt_file": args.prompt_file,
        "notes": args.notes,
        "width": info["width"],
        "height": info["height"],
        "mode_of_image": info["mode"],
        "sha256": info["sha256"],
        "human_confirmed_terms": bool(args.terms_confirmed),
        "license_note": "Confirm the provider's terms and the asset's licence before distribution.",
    }
    sidecar = dest.with_suffix(dest.suffix + ".provenance.json")
    write_json(sidecar, provenance, overwrite=True)
    if args.json:
        print_result(provenance, as_json=True)
    else:
        print(f"Imported {dest} ({info['width']}x{info['height']})")
        print(f"  provenance: {sidecar}")
        if not args.terms_confirmed:
            print("  WARNING: terms not confirmed. Re-run with --terms-confirmed once you have read them.")
        print("  Next: remove_background.py, clean_transparency.py, validate_sprite.py")
    return 0


def cli() -> None:
    """Console-script wrapper with consistent error handling and exit codes."""

    run(main)
