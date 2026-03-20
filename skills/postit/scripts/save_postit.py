#!/usr/bin/env python3
"""Write a postit JSON file into the project .agents/postit tier."""
import argparse
import json
import os
import sys

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, "..", "..", ".."))
if project_root not in sys.path:
  sys.path.insert(0, project_root)
sys.path.insert(0, script_dir)

import postit_store


def main() -> None:
  p = argparse.ArgumentParser(description="Save a postit JSON under the project tier.")
  p.add_argument("--stem", required=True, help="Filename stem (no .json).")
  p.add_argument(
    "--working-directory",
    required=True,
    help="Project root (writes to {wd}/.agents/postit/).",
  )
  p.add_argument(
    "--json-file",
    default=None,
    help="Path to JSON file; if omitted, read JSON from stdin.",
  )
  args = p.parse_args()
  wd = os.path.abspath(args.working_directory)
  if args.json_file:
    with open(args.json_file, encoding="utf-8") as f:
      raw = json.load(f)
  else:
    raw = json.load(sys.stdin)
  path, err = postit_store.write_request(wd, args.stem, raw)
  if err:
    print(json.dumps({"status": "error", "message": err}, indent=2))
    sys.exit(1)
  print(json.dumps({"status": "ok", "path": path}, indent=2))


if __name__ == "__main__":
  main()
