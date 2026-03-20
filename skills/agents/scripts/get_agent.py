import sys
import os
import argparse
import json

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, "..", "..", ".."))
if project_root not in sys.path:
  sys.path.insert(0, project_root)

from utils.db import db_manager


def main():
  parser = argparse.ArgumentParser(description="Get details of a named agent.")
  parser.add_argument("--name", required=True, help="Agent name")
  args = parser.parse_args()

  p = db_manager.get_project_db_path()
  _, rows = db_manager.execute_sync(
    p,
    "SELECT name, description, system_prompt, tool_groups, provider, model FROM agents WHERE name = ?",
    (args.name,),
  )

  if not rows:
    print(f"Error: agent '{args.name}' not found.")
    sys.exit(1)

  name, description, system_prompt, tool_groups, provider, model = rows[0]
  groups = json.loads(tool_groups) if tool_groups else []

  print(f"Name:        {name}")
  print(f"Description: {description or '(none)'}")
  print(f"Provider:    {provider or '(use active)'}")
  print(f"Model:       {model or '(use active)'}")
  print(f"Tool groups: {', '.join(groups) if groups else '(none)'}")
  print()
  print("System prompt:")
  print(system_prompt or "(none)")


if __name__ == "__main__":
  main()
