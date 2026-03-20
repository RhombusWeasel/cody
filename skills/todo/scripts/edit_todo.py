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
  p = argparse.ArgumentParser(description="Edit an existing todo.")
  p.add_argument("--id", type=int, required=True, dest="todo_id", help="Todo row id.")
  p.add_argument("--label", required=True, help="New title.")
  p.add_argument("--text", required=True, help="New description.")
  p.add_argument("--deadline", default=None, help="New deadline or omit for NULL.")
  p.add_argument(
    "--comments",
    default=argparse.SUPPRESS,
    help='Replace comments JSON array of strings, e.g. \'["a","b"]\'.',
  )
  p.add_argument(
    "--completion-note",
    default=argparse.SUPPRESS,
    help="Set completion note (omit to leave unchanged).",
  )
  p.add_argument(
    "--completion-date",
    default=argparse.SUPPRESS,
    help="Set completion date (omit to leave unchanged).",
  )
  args = p.parse_args()
  patch = {}
  if hasattr(args, "comments"):
    patch["comments"] = args.comments
  if hasattr(args, "completion_note"):
    patch["completion_note"] = args.completion_note
  if hasattr(args, "completion_date"):
    patch["completion_date"] = args.completion_date
  result = todo_store.edit_todo(
    args.todo_id,
    args.label,
    args.text,
    args.deadline,
    **patch,
  )
  print(json.dumps(result, indent=2))
  if result.get("status") != "success":
    sys.exit(1)


if __name__ == "__main__":
  main()
