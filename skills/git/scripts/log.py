import argparse
import sys
import os

# Add the project root to sys.path so we can import from the main utils package
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, "..", "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.git_viewer import get_commits
from utils.git import is_git_repo

def main():
  parser = argparse.ArgumentParser(description="Shows recent commit history.")
  parser.add_argument("--path", required=True, help="Path to the git repository.")
  parser.add_argument("--count", type=int, default=10, help="Number of commits to show (default: 10).")
  
  args = parser.parse_args()
  
  if not is_git_repo(args.path):
    print(f"Error: '{args.path}' is not a git repository.")
    sys.exit(1)
    
  commits = get_commits(args.path, args.count)
  
  if not commits:
    print("No commits found.")
    sys.exit(0)
    
  print(f"Recent commits (up to {args.count}):")
  for c in commits:
    print(f"{c['hash']} - {c['time']} - {c['message']}")

if __name__ == "__main__":
  main()
