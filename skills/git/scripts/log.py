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
  parser = argparse.ArgumentParser(description="Shows recent commit history.")
  parser.add_argument("--path", required=True, help="Path to the git repository.")
  parser.add_argument("--count", type=int, default=10, help="Number of commits to show (default: 10).")
  
  args = parser.parse_args()
  
  if not is_git_repo(args.path):
    print(f"Error: '{args.path}' is not a git repository.")
    sys.exit(1)
    
  try:
    repo = git.Repo(args.path)
    if not repo.head.is_valid():
      print("No commits found.")
      sys.exit(0)
      
    commits = list(repo.iter_commits(max_count=args.count))
    if not commits:
      print("No commits found.")
      sys.exit(0)
      
    print(f"Recent commits (up to {args.count}):")
    for c in commits:
      short_hash = c.hexsha[:7] if len(c.hexsha) >= 7 else c.hexsha
      msg = (c.message or "").split("\n")[0].strip()
      time_str = c.committed_datetime.strftime("%Y-%m-%d %H:%M")
      print(f"{short_hash} - {time_str} - {msg}")
  except Exception as e:
    print(f"Error getting commits: {e}")
    sys.exit(1)

if __name__ == "__main__":
  main()
