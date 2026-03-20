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
  p = argparse.ArgumentParser(description="Set a todo's status.")
  p.add_argument("--id", type=int, required=True, dest="todo_id", help="Todo row id.")
  p.add_argument(
    "--status",
    required=True,
    choices=("pending", "completed"),
    help="New status.",
  )
  p.add_argument(
    "--completion-note",
    default=argparse.SUPPRESS,
    help="Required when --status completed: why the task was closed. Ignored for pending.",
  )
  p.add_argument(
    "--completion-date",
    default=argparse.SUPPRESS,
    help="When completing: optional timestamp (e.g. YYYY-MM-DD); default now.",
  )
  args = p.parse_args()
  kw = {}
  if args.status == "completed":
    if not hasattr(args, "completion_note") or not str(args.completion_note).strip():
      p.error("--completion-note is required (non-empty) when using --status completed")
    kw["completion_note"] = str(args.completion_note).strip()
    if hasattr(args, "completion_date"):
      kw["completion_date"] = args.completion_date
    result = todo_store.update_status(args.todo_id, args.status, **kw)
  else:
    result = todo_store.update_status(args.todo_id, args.status)
  print(json.dumps(result, indent=2))
  if result.get("status") != "success":
    sys.exit(1)


if __name__ == "__main__":
  main()
