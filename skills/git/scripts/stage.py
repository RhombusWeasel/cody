import argparse
import sys
import os

# Add the project root to sys.path so we can import from the main utils package
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, "..", "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.git_viewer import stage

def main():
  parser = argparse.ArgumentParser(description="Stages files for commit.")
  parser.add_argument("--path", required=True, help="Path to the git repository.")
  parser.add_argument("--file-path", help="Optional path to a specific file to stage. If omitted, stages all changes.")
  
  args = parser.parse_args()
  
  success = stage(args.path, args.file_path)
  
  if success:
    if args.file_path:
      print(f"Successfully staged {args.file_path}")
    else:
      print("Successfully staged all changes.")
  else:
    print("Failed to stage changes.")
    sys.exit(1)

if __name__ == "__main__":
  main()
