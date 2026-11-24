#!/usr/bin/env python
"""Generate an asset manifest with provenance, file hashes and QA state."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sprite_studio.cli import print_result, run
from sprite_studio.config import ROOT
from sprite_studio.image_utils import write_json
from sprite_studio.manifest import build_manifest, validate_manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("asset_dir")
    parser.add_argument("--brief")
    parser.add_argument("--style")
    parser.add_argument("--animations", help="Directory containing animation YAML specs")
    parser.add_argument("--qa-report")
    parser.add_argument("--provider", default="unknown")
    parser.add_argument("--mode", default="unrecorded")
    parser.add_argument("--model")
    parser.add_argument("--generation-id")
    parser.add_argument("--prompt-file")
    parser.add_argument("--source-file", action="append", help="Source/provenance file; repeatable")
    parser.add_argument("--license", default="Original project asset; verify before distribution.")
    parser.add_argument("--notes", default="")
    parser.add_argument("--output", required=True)
    parser.add_argument("--schema", default="schemas/asset_manifest.schema.json")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    prompt = None
    if args.prompt_file:
        prompt_path = Path(args.prompt_file)
        if not prompt_path.is_file():
            raise FileNotFoundError(args.prompt_file)
        prompt = prompt_path.read_text(encoding="utf-8")
    provenance = {
        "provider": args.provider,
        "mode": args.mode,
        "model_key": args.model,
        "generation_id": args.generation_id,
        "prompt": prompt,
        "prompt_file": args.prompt_file,
        "source_files": args.source_file or [],
        "license": args.license,
        "notes": args.notes,
    }
    output_path = Path(args.output).resolve()
    manifest = build_manifest(
        args.asset_dir,
        brief_path=args.brief,
        style_path=args.style,
        animations_dir=args.animations,
        qa_report_path=args.qa_report,
        provenance=provenance,
        output_path=None,
        # Manifest file paths are relative to the manifest's own folder, so the
        # manifest and exports remain portable as a unit.
        path_base=output_path.parent,
    )
    schema_path = Path(args.schema)
    if not schema_path.is_absolute():
        schema_path = ROOT / schema_path
    ok, errors = validate_manifest(manifest, schema_path if schema_path.is_file() else None)
    manifest["validation"] = {"schema": str(schema_path), "ok": ok, "errors": errors}
    out = Path(args.output)
    if out.exists() and not args.force:
        raise FileExistsError(f"Refusing to overwrite {out}. Pass --force.")
    write_json(out, manifest)
    if args.json:
        print_result(manifest, as_json=True)
    else:
        print(f"Manifest -> {out}")
        print(f"  asset: {manifest['asset_id']}  {manifest['width']}x{manifest['height']}  qa: {manifest['qa']['qa_status']}")
        print(f"  schema: {'PASS' if ok else 'FAIL'}")
        for error in errors:
            print(f"    - {error}")
    return 0 if ok else 1


def cli() -> None:
    """Console-script wrapper with consistent error handling and exit codes."""

    run(main)
