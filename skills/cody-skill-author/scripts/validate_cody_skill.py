#!/usr/bin/env python3
"""
Lightweight checks for a Cody skill directory: SKILL.md frontmatter and coarse hints.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
  try:
    from utils.skills import parse_frontmatter
  except ImportError:
    print("Error: set PYTHONPATH to the Cody repository root.", file=sys.stderr)
    return 1

  parser = argparse.ArgumentParser(description="Validate a Cody skill folder.")
  parser.add_argument("--path", required=True, type=Path, help="Skill root (contains SKILL.md)")
  args = parser.parse_args()

  skill_root = args.path.resolve()
  skill_md = skill_root / "SKILL.md"
  if not skill_md.is_file():
    print(f"Error: missing {skill_md}", file=sys.stderr)
    return 1

  text = skill_md.read_text(encoding="utf-8")
  frontmatter, _body = parse_frontmatter(text)
  name = frontmatter.get("name")
  description = frontmatter.get("description")
  issues = 0

  if not name or not str(name).strip():
    print("Error: frontmatter missing non-empty 'name'.")
    issues += 1
  if not description or not str(description).strip():
    print("Error: frontmatter missing non-empty 'description'.")
    issues += 1

  if issues:
    return 1

  print(f"OK: name={name!r} description present ({len(description)} chars).")

  cmd_dir = skill_root / "cmd"
  if cmd_dir.is_dir():
    py_files = list(cmd_dir.glob("*.py"))
    if not py_files:
      print("Warning: cmd/ exists but has no .py files.")
    else:
      for py in py_files:
        content = py.read_text(encoding="utf-8", errors="replace")
        if "CommandBase" not in content:
          print(f"Warning: {py.name} has no 'CommandBase' substring (expected slash command).")

  tools_dir = skill_root / "tools"
  if tools_dir.is_dir():
    for py in tools_dir.glob("*.py"):
      content = py.read_text(encoding="utf-8", errors="replace")
      if "register_tool" not in content:
        print(f"Warning: {py.name} has no 'register_tool' (expected skill tool).")

  sidebar = skill_root / "components" / "sidebar_tab.py"
  if sidebar.is_file():
    content = sidebar.read_text(encoding="utf-8", errors="replace")
    if "sidebar_label" not in content:
      print("Warning: components/sidebar_tab.py missing sidebar_label.")

  leader = skill_root / "components" / "leader_menu.py"
  if leader.is_file():
    content = leader.read_text(encoding="utf-8", errors="replace")
    if "register_leader" not in content:
      print("Warning: components/leader_menu.py missing register_leader.")

  return 0


if __name__ == "__main__":
  raise SystemExit(main())
