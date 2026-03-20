import argparse
import json
import os
import sys

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, "..", "..", ".."))
if project_root not in sys.path:
  sys.path.insert(0, project_root)
sys.path.insert(0, script_dir)
import todo_store


def main():
  p = argparse.ArgumentParser(description="List todo tasks.")
  p.add_argument(
    "--scope",
    default=None,
    help="Filter by 'global' or a directory path (omit for all scopes).",
  )
  p.add_argument(
    "--status",
    default=None,
    choices=("pending", "completed"),
    help="Filter by status.",
  )
  args = p.parse_args()
  result = todo_store.list_todos(args.scope, args.status)
  if isinstance(result, dict) and result.get("status") == "error":
    print(json.dumps(result, indent=2))
    sys.exit(1)
  print(json.dumps(result, indent=2))


if __name__ == "__main__":
  main()
