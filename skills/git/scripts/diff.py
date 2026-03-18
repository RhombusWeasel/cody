import argparse
import sys
import os

# Add the project root to sys.path so we can import from the main utils package
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, "..", "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.git_viewer import get_diff
from utils.git import is_git_repo

def main():
  parser = argparse.ArgumentParser(description="Shows the git diff.")
  parser.add_argument("--path", required=True, help="Path to the git repository.")
  parser.add_argument("--file-path", help="Optional path to a specific file to diff.")
  parser.add_argument("--staged", action="store_true", help="Show staged changes instead of unstaged.")
  
  args = parser.parse_args()
  
  if not is_git_repo(args.path):
    print(f"Error: '{args.path}' is not a git repository.")
    sys.exit(1)
    
  diff_output = get_diff(args.path, args.file_path, args.staged)
  print(diff_output)

if __name__ == "__main__":
  main()
