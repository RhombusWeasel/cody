#!/usr/bin/env python3
"""List merged postit request stems and the directory that last defined each."""
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
  p = argparse.ArgumentParser(description="List merged postit requests.")
  p.add_argument(
    "--working-directory",
    default=os.getcwd(),
    help="Project working directory (default: cwd).",
  )
  args = p.parse_args()
  wd = os.path.abspath(args.working_directory)
  merged = postit_store.load_merged_requests(wd)
  sources = postit_store.stem_source_map(wd)
  rows = []
  for stem in sorted(merged.keys()):
    rows.append(
      {
        "stem": stem,
        "defined_in": sources.get(stem),
      }
    )
  print(json.dumps(rows, indent=2))


if __name__ == "__main__":
  main()
