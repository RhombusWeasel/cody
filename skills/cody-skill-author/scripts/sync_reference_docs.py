#!/usr/bin/env python3
"""
Copy canonical docs from $CODY_DIR/docs/ into this skill's reference/ folder.

Run after editing docs/extending_cody.md, docs/utils_reference.md, or
docs/password_vault.md. From chat: run_skill cody-skill-author sync_reference_docs.py
or slash command /sync_reference_docs (same behavior).

Requires PYTHONPATH including the Cody repo root (run_skill sets this).
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

_DOCS_NAMES = ("extending_cody.md", "utils_reference.md", "password_vault.md")


def copy_canonical_docs_to_reference(dest_dir: Path) -> tuple[int, list[str]]:
  """
  Copy docs from $CODY_DIR/docs/ into dest_dir.
  Returns (exit_code, log lines). exit_code 0 iff all three files copied.
  """
  try:
    from utils.paths import get_cody_dir
  except ImportError:
    return 1, ["Error: set PYTHONPATH to the Cody repository root."]

  cody_root = Path(get_cody_dir())
  src_dir = cody_root / "docs"
  lines: list[str] = []

  if not src_dir.is_dir():
    lines.append(f"Error: missing docs directory: {src_dir}")
    return 1, lines

  dest_dir.mkdir(parents=True, exist_ok=True)
  copied = 0
  for name in _DOCS_NAMES:
    src = src_dir / name
    if not src.is_file():
      lines.append(f"Warning: skip missing {src}")
      continue
    shutil.copy2(src, dest_dir / name)
    copied += 1
    lines.append(f"Copied {name} -> {dest_dir / name}")

  lines.append(f"Done ({copied} files).")
  code = 0 if copied == len(_DOCS_NAMES) else 1
  return code, lines


def main() -> int:
  dest_dir = Path(__file__).resolve().parent.parent / "reference"
  code, lines = copy_canonical_docs_to_reference(dest_dir)
  for line in lines:
    err = line.startswith("Error") or line.startswith("Warning")
    print(line, file=sys.stderr if err else sys.stdout)
  return code


if __name__ == "__main__":
  raise SystemExit(main())
