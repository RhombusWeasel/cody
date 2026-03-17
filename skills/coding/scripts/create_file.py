import argparse
import sys
import os
from utils.file_ops import check_file_exists, write_file_contents, ensure_indentation

def main():
  parser = argparse.ArgumentParser(description="Creates a new file.")
  parser.add_argument("--path", required=True, help="Path to the file to create.")
  parser.add_argument("--content", required=True, help="Content of the file.")
  
  args = parser.parse_args()
  
  if check_file_exists(args.path):
    print(f"Error: File '{args.path}' already exists.")
    sys.exit(1)
  
  # Ensure directory exists
  os.makedirs(os.path.dirname(args.path), exist_ok=True)
  
  # Decode literal \n and \t from CLI arg (agent often passes escaped strings)
  content = args.content.replace('\\n', '\n').replace('\\t', '\t')
  content = ensure_indentation(content)
  write_file_contents(args.path, content)
  print(f"File '{args.path}' created successfully.")

if __name__ == "__main__":
  main()
