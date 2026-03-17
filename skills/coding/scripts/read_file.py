import argparse
import sys
from utils.file_ops import check_file_exists, read_file_contents

def main():
  parser = argparse.ArgumentParser(description="Reads a file and outputs content with line numbers.")
  parser.add_argument("--path", required=True, help="Path to the file to read.")
  
  args = parser.parse_args()
  
  if not check_file_exists(args.path):
    print(f"Error: File '{args.path}' does not exist.")
    sys.exit(1)
  
  content = read_file_contents(args.path)
  lines = content.split('\n')
  
  for i, line in enumerate(lines):
    print(f"{i + 1:6}|{line}")

if __name__ == "__main__":
  main()
