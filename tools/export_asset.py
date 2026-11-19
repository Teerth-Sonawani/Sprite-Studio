#!/usr/bin/env python
"""Export an approved manifest using a documented engine/profile."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sprite_studio.cli import print_result, run
from sprite_studio.export import export_asset
from sprite_studio.image_utils import read_json
from sprite_studio.manifest import validate_manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("manifest")
    parser.add_argument("--profile", required=True, help="generic_png, generic_sheet, godot_4, unity_2022, aseprite")
    parser.add_argument("--out", required=True)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--allow-unapproved", action="store_true", help="Export a non-APPROVED manifest (clearly marked)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    manifest = read_json(args.manifest)
    qa = manifest.get("qa", {})
    if qa.get("qa_status") != "APPROVED" and not args.allow_unapproved:
        raise ValueError(
            f"Manifest QA status is {qa.get('qa_status')}; refusing to export as production. "
            "Complete visual review or pass --allow-unapproved for a demo export."
        )
    ok, errors = validate_manifest(manifest, Path(__file__).resolve().parents[1] / "schemas" / "asset_manifest.schema.json")
    if not ok:
        raise ValueError("Manifest validation failed: " + "; ".join(errors))
    result = export_asset(manifest, args.manifest, args.profile, args.out, force=args.force)
    if args.json:
        print_result(result, as_json=True)
    else:
        print(f"Exported {manifest['asset_id']} with profile {args.profile}")
        print(f"  output: {result['output_dir']}")
        for path in result["files"]:
            print(f"  - {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run(main))
