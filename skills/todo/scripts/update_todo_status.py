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
  args = p.parse_args()
  result = todo_store.update_status(args.todo_id, args.status)
  print(json.dumps(result, indent=2))
  if result.get("status") != "success":
    sys.exit(1)


if __name__ == "__main__":
  main()
