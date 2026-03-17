import argparse
import sys
from utils.file_ops import check_file_exists, read_file_contents, write_file_contents

def main():
  parser = argparse.ArgumentParser(description="Edits a file by replacing old text with new text.")
  parser.add_argument("--path", required=True, help="Path to the file to edit.")
  parser.add_argument("--old-text", required=True, help="Exact text to replace.")
  parser.add_argument("--new-text", required=True, help="New text to insert.")
  
  args = parser.parse_args()
  
  if not check_file_exists(args.path):
    print(f"Error: File '{args.path}' does not exist.")
    sys.exit(1)
  
  content = read_file_contents(args.path)
  
  # Decode literal \n and \t from CLI args (agent often passes escaped strings)
  old_text = args.old_text.replace('\\n', '\n').replace('\\t', '\t')
  new_text = args.new_text.replace('\\n', '\n').replace('\\t', '\t')
  
  if old_text not in content:
    print(f"Error: The exact text to replace was not found in '{args.path}'.")
    sys.exit(1)
    
  if content.count(old_text) > 1:
    print(f"Error: The text to replace appears multiple times in '{args.path}'. Please provide a more specific text block.")
    sys.exit(1)
  
  new_content = content.replace(old_text, new_text)
  write_file_contents(args.path, new_content)
  print(f"File '{args.path}' updated successfully.")

if __name__ == "__main__":
  main()
