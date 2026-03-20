import argparse
import sys
import os

# Add the project root to sys.path so we can import from the main utils package
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, "..", "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import git
from utils.git import is_git_repo

def main():
  parser = argparse.ArgumentParser(description="Commits staged changes.")
  parser.add_argument("--path", required=True, help="Path to the git repository.")
  parser.add_argument("--message", required=True, help="Commit message.")
  
  args = parser.parse_args()
  
  if not is_git_repo(args.path):
    print(f"Error: '{args.path}' is not a git repository.")
    sys.exit(1)
    
  try:
    repo = git.Repo(args.path)
    repo.index.commit(args.message)
    print("Successfully committed changes.")
  except Exception as e:
    print(f"Failed to commit changes. Are there any staged files? Error: {e}")
    sys.exit(1)

if __name__ == "__main__":
  main()
