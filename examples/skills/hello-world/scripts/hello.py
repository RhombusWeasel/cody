import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description="A simple hello world script.")
    parser.add_argument("--name", type=str, default="World", help="Name to greet")
    args = parser.parse_args()

    print(f"Hello, {args.name}! This is a message from the hello-world skill.")

if __name__ == "__main__":
    main()
