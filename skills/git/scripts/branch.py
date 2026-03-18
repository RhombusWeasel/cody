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
  parser = argparse.ArgumentParser(description="Manage git branches.")
  parser.add_argument("--path", required=True, help="Path to the git repository.")
  parser.add_argument("--list", action="store_true", help="List all local branches.")
  parser.add_argument("--create", help="Create a new branch with the specified name.")
  parser.add_argument("--checkout", help="Checkout the specified branch.")
  
  args = parser.parse_args()
  
  if not is_git_repo(args.path):
    print(f"Error: '{args.path}' is not a git repository.")
    sys.exit(1)
    
  if not any([args.list, args.create, args.checkout]):
    print("Please specify an action: --list, --create, or --checkout")
    sys.exit(1)
    
  try:
    repo = git.Repo(args.path)
  except git.exc.InvalidGitRepositoryError:
    print(f"Error: '{args.path}' is not a valid git repository.")
    sys.exit(1)

  if args.list:
    if not repo.heads:
      print("No branches found.")
    else:
      print("Local branches:")
      current = repo.head.ref.name if repo.head.is_valid() and not repo.head.is_detached else None
      for b in repo.heads:
        prefix = "* " if b.name == current else "  "
        print(f"{prefix}{b.name}")
        
  if args.create:
    try:
      repo.create_head(args.create)
      print(f"Successfully created branch '{args.create}'.")
    except Exception as e:
      print(f"Failed to create branch '{args.create}': {e}")
      sys.exit(1)
      
  if args.checkout:
    try:
      repo.heads[args.checkout].checkout()
      print(f"Successfully checked out branch '{args.checkout}'.")
    except IndexError:
      print(f"Failed to checkout branch '{args.checkout}': Branch not found")
      sys.exit(1)
    except Exception as e:
      err_msg = getattr(e, "stderr", str(e)).strip()
      print(f"Failed to checkout branch '{args.checkout}': {err_msg}")
      sys.exit(1)

if __name__ == "__main__":
  main()
