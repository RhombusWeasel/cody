"""Run via run_skill: brave-search / search_web.py with --query."""

import argparse
import json
import os
import sys

_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.abspath(os.path.join(_script_dir, "..", "..", ".."))
if _project_root not in sys.path:
  sys.path.insert(0, _project_root)

from utils.cfg_man import cfg  # noqa: E402

import utils.providers  # noqa: F401, E402
import utils.agent  # noqa: F401, E402
import utils.skills  # noqa: F401, E402
import utils.cmd_loader  # noqa: F401, E402
import utils.db  # noqa: F401, E402
import utils.interface_defaults  # noqa: F401, E402
import skills.brave_search.api  # noqa: F401, E402


def main() -> None:
  parser = argparse.ArgumentParser(description="Brave Web Search (JSON on stdout).")
  parser.add_argument("--query", required=True, help="Search query")
  parser.add_argument("--limit", type=int, default=None, help="Max results (capped at 20)")
  args = parser.parse_args()

  working_dir = os.environ.get("CODY_WORKING_DIRECTORY", os.getcwd())
  cfg.load_project_config(working_dir)
  cfg.apply_registered_defaults()
  cfg.set("session.working_directory", working_dir)

  from skills.brave_search.api import BRAVE_SEARCH_ENV_TOKEN, fetch_brave_web_search

  token = (os.environ.get(BRAVE_SEARCH_ENV_TOKEN) or "").strip()
  if not token:
    print(
      json.dumps(
        {
          "error": (
            "Missing API token in environment. In Cody, unlock the password vault and run again "
            "(run_skill injects the token when the vault is unlocked)."
          )
        }
      )
    )
    sys.exit(1)

  try:
    results = fetch_brave_web_search(args.query, limit=args.limit, api_token=token)
    print(json.dumps({"query": args.query, "results": results}, indent=2))
  except ValueError as e:
    print(json.dumps({"error": str(e)}))
    sys.exit(1)
  except Exception as e:
    print(json.dumps({"error": str(e)}))
    sys.exit(1)


if __name__ == "__main__":
  main()
