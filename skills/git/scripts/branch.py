import argparse
import sys
import os

# Add the project root to sys.path so we can import from the main utils package
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, "..", "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.git_viewer import get_branches, create_branch, checkout_branch

def main():
  parser = argparse.ArgumentParser(description="Manage git branches.")
  parser.add_argument("--path", required=True, help="Path to the git repository.")
  parser.add_argument("--list", action="store_true", help="List all local branches.")
  parser.add_argument("--create", help="Create a new branch with the specified name.")
  parser.add_argument("--checkout", help="Checkout the specified branch.")
  
  args = parser.parse_args()
  
  if not any([args.list, args.create, args.checkout]):
    print("Please specify an action: --list, --create, or --checkout")
    sys.exit(1)
    
  if args.list:
    branches = get_branches(args.path)
    if not branches:
      print("No branches found or not a git repository.")
    else:
      print("Local branches:")
      for b in branches:
        prefix = "* " if b["is_current"] else "  "
        print(f"{prefix}{b['name']}")
        
  if args.create:
    success = create_branch(args.path, args.create)
    if success:
      print(f"Successfully created branch '{args.create}'.")
    else:
      print(f"Failed to create branch '{args.create}'.")
      sys.exit(1)
      
  if args.checkout:
    success, err_msg = checkout_branch(args.path, args.checkout)
    if success:
      print(f"Successfully checked out branch '{args.checkout}'.")
    else:
      print(f"Failed to checkout branch '{args.checkout}': {err_msg}")
      sys.exit(1)

if __name__ == "__main__":
  main()
