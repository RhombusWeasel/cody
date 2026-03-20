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
  p = argparse.ArgumentParser(description="Add a todo task.")
  p.add_argument("--label", required=True, help="Short title for the task.")
  p.add_argument(
    "--scope",
    required=True,
    help="'global' or the project working directory path.",
  )
  p.add_argument("--text", required=True, help="Detailed description.")
  p.add_argument("--deadline", default=None, help="Optional deadline (e.g. YYYY-MM-DD).")
  p.add_argument(
    "--comments",
    default=None,
    help='Optional JSON array of strings, e.g. \'["first note"]\'. Default [].',
  )
  args = p.parse_args()
  result = todo_store.add_todo(
    args.label,
    args.scope,
    args.text,
    args.deadline,
    comments=args.comments,
  )
  print(json.dumps(result, indent=2))
  if result.get("status") != "success":
    sys.exit(1)


if __name__ == "__main__":
  main()
