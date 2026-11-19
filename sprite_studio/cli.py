"""Small CLI helpers shared by tools/ scripts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .errors import StudioError


def add_json_flag(parser):
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON to stdout")
    return parser


def print_result(data, as_json: bool = False, human: str | None = None):
    if as_json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    elif human is not None:
        print(human)
    else:
        print(json.dumps(data, indent=2, ensure_ascii=False))


def run(main):
    """Run a tool entry point with consistent error handling and exit codes."""

    try:
        result = main()
        if isinstance(result, int):
            raise SystemExit(result)
        return 0
    except StudioError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(exc.exit_code)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
    except FileExistsError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        raise SystemExit(130)


def resolve_path(value: str | None) -> Path | None:
    return Path(value) if value else None
