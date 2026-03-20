import argparse
import sys
import os

# Add the project root to sys.path so we can import from the main utils package
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, "..", "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import git
from utils.git import is_git_repo, get_file_status

def main():
  parser = argparse.ArgumentParser(description="Shows the current git status.")
  parser.add_argument("--path", required=True, help="Path to the git repository.")
  
  args = parser.parse_args()
  
  if not is_git_repo(args.path):
    print(f"Error: '{args.path}' is not a git repository.")
    sys.exit(1)
    
  try:
    repo = git.Repo(args.path)
    status = get_file_status(repo)
    staged = status["staged"]
    unstaged = status["unstaged"]
    untracked = status["untracked"]
      
    if not staged and not unstaged and not untracked:
      print("No changes (working tree clean).")
      sys.exit(0)
      
    if staged:
      print("Staged changes:")
      for s in staged:
        print(f"  {s['status']} {s['path']}")
      print()
        
    if unstaged:
      print("Unstaged changes:")
      for s in unstaged:
        print(f"  {s['status']} {s['path']}")
      print()
        
    if untracked:
      print("Untracked files:")
      for s in untracked:
        print(f"  {s['status']} {s['path']}")
      print()
      
  except Exception as e:
    print(f"Error getting status: {e}")
    sys.exit(1)

if __name__ == "__main__":
  main()
