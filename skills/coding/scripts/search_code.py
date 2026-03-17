import argparse
import sys
import os
import re
from utils.file_ops import read_file_contents

def search_in_file(file_path, pattern):
  try:
    content = read_file_contents(file_path)
    lines = content.split('\n')
    matches = []
    
    for i, line in enumerate(lines):
      if re.search(pattern, line):
        matches.append((i + 1, line))
        
    return matches
  except Exception as e:
    return []

def main():
  parser = argparse.ArgumentParser(description="Searches for specific strings or regex patterns across the workspace.")
  parser.add_argument("--pattern", required=True, help="Regex pattern or string to search for.")
  parser.add_argument("--path", default=".", help="Directory to search in. Defaults to current directory.")
  
  args = parser.parse_args()
  
  if not os.path.exists(args.path):
    print(f"Error: Path '{args.path}' does not exist.")
    sys.exit(1)
    
  print(f"Searching for '{args.pattern}' in '{args.path}'...\n")
  
  found_matches = False
  
  if os.path.isfile(args.path):
    matches = search_in_file(args.path, args.pattern)
    if matches:
      found_matches = True
      print(f"--- {args.path} ---")
      for line_num, line in matches:
        print(f"{line_num:6}|{line}")
  else:
    for root, _, files in os.walk(args.path):
      # Skip hidden directories like .git
      if '/.' in root or root.startswith('.'):
        if root != '.':
          continue
          
      for file in files:
        # Skip hidden files
        if file.startswith('.'):
          continue
          
        file_path = os.path.join(root, file)
        matches = search_in_file(file_path, args.pattern)
        
        if matches:
          found_matches = True
          print(f"--- {file_path} ---")
          for line_num, line in matches:
            print(f"{line_num:6}|{line}")
            
  if not found_matches:
    print("No matches found.")

if __name__ == "__main__":
  main()
