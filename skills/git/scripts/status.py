import argparse
import sys
import os

# Add the project root to sys.path so we can import from the main utils package
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, "..", "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.git_viewer import get_status

def main():
  parser = argparse.ArgumentParser(description="Shows the current git status.")
  parser.add_argument("--path", required=True, help="Path to the git repository.")
  
  args = parser.parse_args()
  
  status_list = get_status(args.path)
  
  if not status_list:
    print("No changes or not a git repository.")
    sys.exit(0)
    
  staged = [s for s in status_list if s["staged"]]
  unstaged = [s for s in status_list if not s["staged"] and s["status"] != "??"]
  untracked = [s for s in status_list if not s["staged"] and s["status"] == "??"]
  
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

if __name__ == "__main__":
  main()
