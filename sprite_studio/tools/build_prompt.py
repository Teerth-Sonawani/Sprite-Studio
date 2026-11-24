#!/usr/bin/env python
"""Build a provider-agnostic generation prompt from a brief and style profile."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sprite_studio.cli import print_result, run
from sprite_studio.manifest import _load_structured
from sprite_studio.prompting import build_prompt, negative_prompt


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("brief", help="Asset brief YAML/JSON")
    parser.add_argument("--style", help="Style guide/profile YAML/JSON")
    parser.add_argument("--output", help="Write the prompt to this file")
    parser.add_argument("--negative-output", help="Write the negative prompt to this file")
    parser.add_argument("--extra-notes", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    brief = _load_structured(args.brief)
    style = _load_structured(args.style) if args.style else {}
    prompt = build_prompt(brief, style, extra_notes=args.extra_notes)
    negative = negative_prompt(brief, style)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(prompt, encoding="utf-8")
    if args.negative_output:
        Path(args.negative_output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.negative_output).write_text(negative + "\n", encoding="utf-8")
    result = {"prompt": prompt, "negative_prompt": negative, "output": args.output}
    if args.json:
        print_result(result, as_json=True)
    else:
        print(prompt)
        print("NEGATIVE PROMPT:")
        print(negative)
        if args.output:
            print(f"\nPrompt written to {args.output}", file=sys.stderr)
    return 0


def cli() -> None:
    """Console-script wrapper with consistent error handling and exit codes."""

    run(main)
