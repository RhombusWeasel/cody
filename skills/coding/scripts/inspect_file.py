#!/usr/bin/env python3
"""
inspect_file.py — Code-aware file inspector.

Provides structured overviews and section extraction for source files.
Supports pluggable language parsers (Python AST, Lua regex, etc.).

Usage:
  inspect_file.py --path <file> [options]

Options:
  --path <file>         Path to the file to inspect (required)
  --summary             Show a table-of-contents summary (default if no section filter)
  --function <name>     Extract a specific function by name
  --class <name>        Extract a specific class by name
  --section <name>      Extract a specific section by name (class, function, etc.)
  --lines <start-end>   Extract a specific line range, e.g. "10-45"
  --context <N>         Show N lines of surrounding context (used with --function/--class/--section)
  --format <text|json>  Output format (default: text)
  --list-parsers        List all registered language parsers and exit
"""

import argparse
import json
import os
import sys

# Ensure scripts directory is on path for parser imports
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from utils.file_ops import check_file_exists, read_file_contents
from parsers import get_parser, list_parsers


def _extract_lines(content: str, start: int, end: int, context: int = 0) -> str:
    """Extract lines from content with line numbers and optional context."""
    lines = content.split("\n")

    # Apply context
    ctx_start = max(0, start - 1 - context)
    ctx_end = min(len(lines), end + context)

    result = []
    for i in range(ctx_start, ctx_end):
        line_num = i + 1
        prefix = " "
        if context > 0:
            if line_num < start or line_num > end:
                prefix = "·"  # context marker
            else:
                prefix = ">"  # target marker
        result.append(f"{prefix}{line_num:6}|{lines[i]}")

    return "\n".join(result)


def _find_section(result, name: str, kind: str = None) -> dict | None:
    """Find a section by name, optionally filtering by kind."""
    for section in result.sections:
        if section["name"] == name:
            if kind is None or section["kind"] == kind:
                return section
    return None


def _find_function(result, name: str) -> dict | None:
    """Find a function by name."""
    for fn in result.functions:
        if fn["name"] == name:
            return fn
    return None


def _find_class(result, name: str) -> dict | None:
    """Find a class by name."""
    for cls in result.classes:
        if cls["name"] == name:
            return cls
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Code-aware file inspector with structural analysis and section extraction."
    )
    parser.add_argument("--path", help="Path to the file to inspect.")
    parser.add_argument("--summary", action="store_true", help="Show a table-of-contents summary.")
    parser.add_argument("--function", type=str, help="Extract a specific function by name.")
    parser.add_argument("--class", dest="class_name", type=str, help="Extract a specific class by name.")
    parser.add_argument("--section", type=str, help="Extract a specific section by name.")
    parser.add_argument("--lines", type=str, help="Extract a specific line range, e.g. '10-45'.")
    parser.add_argument("--context", type=int, default=0, help="Show N lines of surrounding context.")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format.")
    parser.add_argument("--list-parsers", action="store_true", help="List all registered parsers.")

    args = parser.parse_args()

    # ── List parsers mode ──
    if args.list_parsers:
        available = list_parsers()
        if available:
            print("Registered parsers:")
            for lang in available:
                print(f"  • {lang}")
        else:
            print("No parsers registered.")
        sys.exit(0)

    # ── Validate path (not required for --list-parsers) ──
    if not args.path:
        print("Error: --path is required.", file=sys.stderr)
        sys.exit(1)

    # ── Validate path is provided ──
    if not args.path:
        print("Error: --path is required (except with --list-parsers).", file=sys.stderr)
        sys.exit(1)

    # ── Validate file ──
    if not check_file_exists(args.path):
        print(f"Error: File '{args.path}' does not exist.", file=sys.stderr)
        sys.exit(1)

    content = read_file_contents(args.path)
    total_lines = len(content.split("\n"))

    # ── Get parser ──
    lang_parser = get_parser(args.path)

    # ── Determine mode ──
    has_section_filter = bool(args.function or args.class_name or args.section or args.lines)

    # If no specific action requested, default to summary
    if not has_section_filter and not args.summary:
        args.summary = True

    # ── Summary mode ──
    if args.summary and not has_section_filter:
        if lang_parser:
            result = lang_parser.parse(args.path, content)
            if args.format == "json":
                print(json.dumps(result.to_json(), indent=2))
            else:
                print(result.to_summary())
        else:
            # No parser available — show basic file info
            ext = os.path.splitext(args.path)[1]
            print(f"📄 {args.path} — {total_lines} lines (unknown: '{ext}')")
            print("─" * 60)
            print(f"No parser registered for '{ext}' files.")
            print(f"Registered parsers: {', '.join(list_parsers()) or 'none'}")
            print("\nFalling back to raw file read:\n")
            lines = content.split("\n")
            for i, line in enumerate(lines):
                print(f"{i + 1:6}|{line}")
        sys.exit(0)

    # ── Section extraction modes ──
    if not lang_parser:
        print(f"Error: No parser registered for '{os.path.splitext(args.path)[1]}' files.", file=sys.stderr)
        print(f"Registered parsers: {', '.join(list_parsers()) or 'none'}", file=sys.stderr)
        sys.exit(1)

    result = lang_parser.parse(args.path, content)

    # ── Line range extraction ──
    if args.lines:
        try:
            parts = args.lines.split("-")
            if len(parts) == 2:
                start = int(parts[0].strip())
                end = int(parts[1].strip())
            elif len(parts) == 1:
                start = int(parts[0].strip())
                end = start
            else:
                print(f"Error: Invalid line range '{args.lines}'. Use format 'start-end'.", file=sys.stderr)
                sys.exit(1)

            if start < 1 or end > total_lines:
                print(f"Error: Line range {start}-{end} is out of bounds (file has {total_lines} lines).", file=sys.stderr)
                sys.exit(1)

            extracted = _extract_lines(content, start, end, args.context)
            print(f"📄 {args.path} — lines {start}-{end}" + (f" (with {args.context} lines context)" if args.context else ""))
            print("─" * 60)
            print(extracted)
            sys.exit(0)
        except ValueError:
            print(f"Error: Invalid line range '{args.lines}'. Use format 'start-end'.", file=sys.stderr)
            sys.exit(1)

    # ── Function extraction ──
    if args.function:
        fn = _find_function(result, args.function)
        if not fn:
            # Try case-insensitive search
            matches = [f for f in result.functions if f["name"].lower() == args.function.lower()]
            if matches:
                fn = matches[0]
            else:
                # List available functions
                names = [f["name"] for f in result.functions]
                print(f"Error: Function '{args.function}' not found.", file=sys.stderr)
                if names:
                    print(f"Available functions: {', '.join(names)}", file=sys.stderr)
                sys.exit(1)

        extracted = _extract_lines(content, fn["line"], fn["end_line"], args.context)
        prefix = "async " if fn.get("async") else ""
        deco = "\n".join(fn.get("decorators", []))
        parent = f" (in {fn['parent']})" if fn.get("parent") else ""

        print(f"📄 {args.path} — {prefix}def {fn['name']}{parent} (lines {fn['line']}-{fn['end_line']})" + (f" [+{args.context} ctx]" if args.context else ""))
        print("─" * 60)
        if deco:
            print(deco)
        print(extracted)
        sys.exit(0)

    # ── Class extraction ──
    if args.class_name:
        cls = _find_class(result, args.class_name)
        if not cls:
            matches = [c for c in result.classes if c["name"].lower() == args.class_name.lower()]
            if matches:
                cls = matches[0]
            else:
                names = [c["name"] for c in result.classes]
                print(f"Error: Class '{args.class_name}' not found.", file=sys.stderr)
                if names:
                    print(f"Available classes: {', '.join(names)}", file=sys.stderr)
                sys.exit(1)

        extracted = _extract_lines(content, cls["line"], cls["end_line"], args.context)
        deco = "\n".join(cls.get("decorators", []))

        print(f"📄 {args.path} — class {cls['name']} (lines {cls['line']}-{cls['end_line']})" + (f" [+{args.context} ctx]" if args.context else ""))
        print("─" * 60)
        if deco:
            print(deco)
        print(extracted)
        sys.exit(0)

    # ── Generic section extraction ──
    if args.section:
        section = _find_section(result, args.section)
        if not section:
            # Try matching by kind:name pattern
            for s in result.sections:
                if s["name"].lower() == args.section.lower():
                    section = s
                    break
            if not section:
                names = [s["name"] for s in result.sections]
                print(f"Error: Section '{args.section}' not found.", file=sys.stderr)
                if names:
                    print(f"Available sections: {', '.join(names)}", file=sys.stderr)
                sys.exit(1)

        extracted = _extract_lines(content, section["line"], section["end_line"], args.context)
        print(f"📄 {args.path} — {section['kind']} '{section['name']}' (lines {section['line']}-{section['end_line']})" + (f" [+{args.context} ctx]" if args.context else ""))
        print("─" * 60)
        print(extracted)
        sys.exit(0)


if __name__ == "__main__":
    main()
