#!/usr/bin/env python3
"""
Create a new Cody skill directory with stubs for common extension points.

Default: full minimal tree (SKILL.md, scripts/hello.py, cmd, tools, sidebar+CSS, leader).
Use --minimal for SKILL.md + scripts/hello.py only.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _resolve_target_root(target: str) -> Path:
  if target == "bundled":
    from utils.paths import get_cody_dir
    return Path(get_cody_dir()) / "skills"
  if target == "user":
    return Path.home() / ".agents" / "skills"
  if target == "project":
    wd = os.environ.get("CODY_WORKING_DIRECTORY") or os.getcwd()
    return Path(wd) / ".agents" / "skills"
  raise ValueError(f"unknown target: {target}")


def _write(path: Path, content: str) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(content, encoding="utf-8")


def _skill_md(frontmatter_name: str, description: str, title: str, include_scripts: bool) -> str:
  scripts_block = ""
  if include_scripts:
    scripts_block = f"""

## Available Scripts

Run via `run_skill` with `skill_name` set to the frontmatter `name` below.

### hello

```json
{{
  "function": "run_skill",
  "arguments": {{
    "skill_name": "{frontmatter_name}",
    "script_name": "hello.py",
    "args": ""
  }}
}}
```
"""

  return f"""---
name: {frontmatter_name}
description: {description}
---

# {title}

Replace this body with skill-specific instructions for the agent.{scripts_block}
"""


def _file_cmd_example() -> str:
  return '''from utils.cmd_loader import CommandBase
from components.utils.input_modal import preview_then_append_chat_message


class ExampleCommand(CommandBase):
  description = "Example slash command: /example [text…] (preview, then add to chat)"

  async def execute(self, app, args: list[str]):
    try:
      text = " ".join(args) if args else "(nothing)"
      await preview_then_append_chat_message(app, "Example", text)
    except Exception as e:
      print(f"example command failed: {e}")
'''


def _file_tools_example(frontmatter_name: str) -> str:
  tool_name = "example_ping_" + frontmatter_name.replace("-", "_")
  return f'''from utils.tool import register_tool


def example_ping(message: str = "pong") -> str:
  """
  Example skill-local tool. Echoes a short string for testing.
  :param message: Text to echo back.
  :return: The same message.
  """
  return message


register_tool(
  "{tool_name}",
  example_ping,
  tags=["example"],
)
'''


def _file_sidebar_tab(title: str) -> str:
  safe = title.replace('"', "'")
  return f'''from textual.widgets import Static

sidebar_label = "{safe}"
sidebar_tooltip = "Example skill sidebar tab"


class SidebarWidget(Static):
  def compose(self):
    yield Static("Replace with your skill UI.")
'''


def _file_sidebar_css() -> str:
  return """/* Example skill component styles */
"""


def _file_leader_menu() -> str:
  return '''def register_leader(reg):
  """Example leader chords; customize or remove."""

  async def example_action(app):
    app.notify("Leader action from skill", severity="information")

  reg.add_submenu((), "s", "Skill example")
  reg.add_action(("s",), "x", "Notify test", example_action)
'''


def _file_hello_py() -> str:
  return '''#!/usr/bin/env python3
"""Minimal script; run via run_skill."""
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--name", default="world", help="Greeting target")
args = parser.parse_args()
print(f"Hello, {args.name}!")
'''


def main() -> int:
  parser = argparse.ArgumentParser(description="Scaffold a Cody skill directory.")
  parser.add_argument("--target", choices=("project", "user", "bundled"), default="project")
  parser.add_argument("--skill-dir-name", required=True, help="Filesystem folder name under skills tier")
  parser.add_argument("--frontmatter-name", required=True, help="YAML name in SKILL.md (catalog id)")
  parser.add_argument("--description", default="Custom Cody skill (scaffolded).", help="YAML description")
  parser.add_argument("--title", default="", help="H1 title in SKILL.md body (default: derived from dir name)")
  parser.add_argument("--minimal", action="store_true", help="Only SKILL.md + scripts/hello.py")
  parser.add_argument("--force", action="store_true", help="Overwrite existing skill directory")
  args = parser.parse_args()

  title = args.title.strip() or args.skill_dir_name.replace("-", " ").title()
  try:
    root = _resolve_target_root(args.target)
  except ImportError:
    print("Error: set PYTHONPATH to the Cody repository root for --target bundled.", file=sys.stderr)
    return 1
  skill_root = root / args.skill_dir_name

  if skill_root.exists() and not args.force:
    print(f"Error: already exists (use --force): {skill_root}", file=sys.stderr)
    return 1
  if skill_root.exists() and args.force:
    import shutil
    shutil.rmtree(skill_root)

  include_scripts = True
  _write(skill_root / "SKILL.md", _skill_md(args.frontmatter_name, args.description, title, include_scripts))
  _write(skill_root / "scripts" / "hello.py", _file_hello_py())

  if not args.minimal:
    _write(skill_root / "cmd" / "example.py", _file_cmd_example())
    _write(skill_root / "tools" / "example_tool.py", _file_tools_example(args.frontmatter_name))
    _write(skill_root / "components" / "sidebar_tab.py", _file_sidebar_tab(title))
    _write(skill_root / "components" / "example_skill.css", _file_sidebar_css())
    _write(skill_root / "components" / "leader_menu.py", _file_leader_menu())

  print(f"Scaffolded skill at: {skill_root}")
  print("Restart Cody to load new cmd/, tools/, and components/.")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
