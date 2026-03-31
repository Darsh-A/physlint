from __future__ import annotations

import argparse
import json
import pathlib
import sys

from physlint.config import Config, load_config
from physlint.engine import Diagnostic, analyze

_INFO_CODES = {"UNIT_INFERRED"}


def _collect_files(paths: list[str], recursive: bool) -> list[pathlib.Path]:
    result: list[pathlib.Path] = []
    for p in paths:
        path = pathlib.Path(p)
        if path.is_file():
            result.append(path)
        elif path.is_dir() and recursive:
            result.extend(sorted(path.rglob("*.py")))
        elif path.is_dir():
            result.extend(sorted(path.glob("*.py")))
    return result


def _format_text(filepath: pathlib.Path, diag: Diagnostic) -> str:
    return f"{filepath}:{diag.line}:{diag.col}: {diag.code:<18s} {diag.message}"


def _format_json(filepath: pathlib.Path, diag: Diagnostic) -> dict:
    return {
        "file": str(filepath),
        "line": diag.line,
        "col": diag.col,
        "code": diag.code,
        "message": diag.message,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="physlint",
        description="Static analysis for physical unit consistency in Python",
    )
    ap.add_argument("paths", nargs="+", help="files or directories to analyze")
    ap.add_argument("--json", dest="json_output", action="store_true",
                    help="output diagnostics as JSON")
    ap.add_argument("-r", "--recursive", action="store_true",
                    help="recursively scan directories")
    ap.add_argument("--strict", action="store_true", default=None,
                    help="enable strict mode")
    ap.add_argument("--no-strict-scale", dest="strict_scale_off", action="store_true",
                    help="disable strict scale checking")
    ap.add_argument("--ignore-prefix", action="append", default=None,
                    help="ignore variables starting with prefix (repeatable)")
    ap.add_argument("--config", type=str, default=None,
                    help="path to physlint.toml config file")
    args = ap.parse_args(argv)

    config_path = pathlib.Path(args.config) if args.config else None
    config = load_config(config_path)

    if args.strict is not None:
        config.strict = args.strict
    if args.strict_scale_off:
        config.strict_scale = False
    if args.ignore_prefix:
        config.ignore_prefix.extend(args.ignore_prefix)

    files = _collect_files(args.paths, args.recursive)
    if not files:
        print("physlint: no Python files found", file=sys.stderr)
        return 1

    all_json: list[dict] = []
    has_errors = False

    for filepath in files:
        source = filepath.read_text(encoding="utf-8")
        for diag in analyze(source, config):
            if diag.code not in _INFO_CODES:
                has_errors = True
            if args.json_output:
                all_json.append(_format_json(filepath, diag))
            else:
                print(_format_text(filepath, diag))

    if args.json_output:
        print(json.dumps(all_json, indent=2))

    return 1 if has_errors else 0


if __name__ == "__main__":
    sys.exit(main())
