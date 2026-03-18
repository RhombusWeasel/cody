import argparse
import sys
import os

# Add the project root to sys.path so we can import from the main utils package
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, "..", "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import git
from utils.git import is_git_repo, stage_all

def main():
  parser = argparse.ArgumentParser(description="Stages files for commit.")
  parser.add_argument("--path", required=True, help="Path to the git repository.")
  parser.add_argument("--file-path", help="Optional path to a specific file to stage. If omitted, stages all changes.")
  
  args = parser.parse_args()
  
  if not is_git_repo(args.path):
    print(f"Error: '{args.path}' is not a git repository.")
    sys.exit(1)
    
  try:
    repo = git.Repo(args.path)
    if args.file_path:
      repo.index.add([args.file_path])
      print(f"Successfully staged {args.file_path}")
    else:
      stage_all(repo)
      print("Successfully staged all changes.")
  except Exception as e:
    print(f"Failed to stage changes: {e}")
    sys.exit(1)

if __name__ == "__main__":
  main()
