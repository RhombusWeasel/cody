#!/usr/bin/env python3
"""Execute one merged postit request by stem and print JSON result."""
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

MAX_BODY = 200_000


def main() -> None:
  p = argparse.ArgumentParser(description="Run a saved postit HTTP request.")
  p.add_argument("--name", required=True, help="Request stem (filename without .json).")
  p.add_argument(
    "--working-directory",
    default=os.getcwd(),
    help="Project working directory (default: cwd).",
  )
  p.add_argument(
    "--timeout",
    type=float,
    default=30.0,
    help="Request timeout in seconds (default: 30).",
  )
  args = p.parse_args()
  wd = os.path.abspath(args.working_directory)
  merged = postit_store.load_merged_requests(wd)
  raw = merged.get(args.name)
  if raw is None:
    print(
      json.dumps(
        {"status": "error", "message": f"unknown postit stem: {args.name}"},
        indent=2,
      )
    )
    sys.exit(1)
  norm, err = postit_store.normalize_request(raw)
  if err:
    print(json.dumps({"status": "error", "message": err}, indent=2))
    sys.exit(1)
  try:
    resp = postit_store.execute_request(norm, timeout=args.timeout)
  except Exception as e:
    print(
      json.dumps(
        {
          "status": "error",
          "message": str(e),
          "type": type(e).__name__,
        },
        indent=2,
      )
    )
    sys.exit(1)
  text = resp.text
  if len(text) > MAX_BODY:
    text = text[:MAX_BODY] + "\n… [truncated]"
  out = {
    "status": "ok",
    "status_code": resp.status_code,
    "reason": resp.reason,
    "headers": dict(resp.headers),
    "text": text,
  }
  print(json.dumps(out, indent=2))


if __name__ == "__main__":
  main()
