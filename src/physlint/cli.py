from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

from physlint.config import Config, load_config
from physlint.engine import Diagnostic, analyze

_LEVELS: dict[str, tuple[str, str]] = {
    "UNIT_MISMATCH":  ("error",   "31"),
    "UNIT_CONFLICT":  ("error",   "31"),
    "SCALE_MISMATCH": ("warning", "33"),
    "SCALE_CONFLICT": ("warning", "33"),
    "UNIT_INFERRED":  ("info",    "36"),
}

_use_color = sys.stderr.isatty() and os.environ.get("NO_COLOR") is None


def _c(code: str, text: str) -> str:
    if not _use_color:
        return text
    return f"\033[{code}m{text}\033[0m"


def _bold(text: str) -> str:
    return _c("1", text)


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


def _print_diag(filepath: pathlib.Path, diag: Diagnostic, source_lines: list[str]) -> None:
    level, color = _LEVELS.get(diag.code, ("info", "36"))
    label = _c(f"1;{color}", level)
    code = _c("2", diag.code)
    location = _c("1", f"{filepath}:{diag.line}:{diag.col}")

    print(f"  {location}  {label}  {diag.message}  {code}")

    if 1 <= diag.line <= len(source_lines):
        line_text = source_lines[diag.line - 1].rstrip()
        gutter = _c("2", f"  {diag.line:>4} |")
        print(f"  {gutter} {line_text}")
        marker = " " * diag.col + _c(f"1;{color}", "^")
        blank_gutter = _c("2", "       |")
        print(f"  {blank_gutter} {marker}")


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
    counts: dict[str, int] = {"error": 0, "warning": 0, "info": 0}

    for filepath in files:
        source = filepath.read_text(encoding="utf-8")
        diags = analyze(source, config)
        if not diags:
            continue

        if not args.json_output:
            print()
            print(_bold(str(filepath)))

        source_lines = source.splitlines()
        for diag in diags:
            level, _ = _LEVELS.get(diag.code, ("info", "36"))
            counts[level] += 1
            if args.json_output:
                all_json.append(_format_json(filepath, diag))
            else:
                _print_diag(filepath, diag, source_lines)

    if args.json_output:
        print(json.dumps(all_json, indent=2))
    else:
        parts = []
        if counts["error"]:
            parts.append(_c("1;31", f"{counts['error']} error{'s' if counts['error'] != 1 else ''}"))
        if counts["warning"]:
            parts.append(_c("1;33", f"{counts['warning']} warning{'s' if counts['warning'] != 1 else ''}"))
        if counts["info"]:
            parts.append(_c("36", f"{counts['info']} info"))
        if parts:
            print()
            print("  " + ", ".join(parts))
            print()
        elif files:
            print(_c("32", "  all clean"))
            print()

    has_errors = counts["error"] > 0 or counts["warning"] > 0
    return 1 if has_errors else 0


if __name__ == "__main__":
    sys.exit(main())
