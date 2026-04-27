import argparse
import sys
import os

def main():
    parser = argparse.ArgumentParser(description="Writes content to a file, creating directories as needed.")
    parser.add_argument("--path", required=True, help="Path to the file to write.")
    parser.add_argument("--content", help="Content of the file. If omitted, reads from stdin.")
    
    args = parser.parse_args()
    
    # Get content: from --content arg or stdin
    if args.content:
        content = args.content
    else:
        if sys.stdin.isatty():
            print("Error: No content provided. Use --content or pipe content via stdin.", file=sys.stderr)
            sys.exit(1)
        content = sys.stdin.read()
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(args.path) or ".", exist_ok=True)
    
    # Write the file (creates or overwrites)
    with open(args.path, "w") as f:
        f.write(content)
    
    print(f"File '{args.path}' written successfully.")

if __name__ == "__main__":
    main()
