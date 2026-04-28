import json
import os
from utils.tool import register_tool


def read_file(path: str, start_line: int = None, end_line: int = None):
    """
    Read the contents of a file, optionally restricting to a line range.
    Args:
        path: Path to the file to read.
        start_line: Optional 1-based start line (inclusive). If omitted, reads from line 1.
        end_line: Optional 1-based end line (inclusive). If omitted, reads to end of file.
    Returns:
        A JSON string with the file content, line count, and any error.
    """
    try:
        with open(path, "r") as f:
            lines = f.readlines()
    except FileNotFoundError:
        return json.dumps({
            "function": "read_file",
            "arguments": {"path": path, "start_line": start_line, "end_line": end_line},
            "result": f"Error: File not found: {path}"
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "function": "read_file",
            "arguments": {"path": path, "start_line": start_line, "end_line": end_line},
            "result": f"Error reading file: {str(e)}"
        }, indent=2)

    total_lines = len(lines)

    # Normalise line range
    s = (start_line - 1) if start_line is not None else 0
    e = end_line if end_line is not None else total_lines

    # Clamp to valid range
    s = max(0, s)
    e = min(total_lines, e)

    if s >= e:
        return json.dumps({
            "function": "read_file",
            "arguments": {"path": path, "start_line": start_line, "end_line": end_line},
            "result": f"Error: empty line range ({start_line}–{end_line}) in file with {total_lines} lines."
        }, indent=2)

    selected = lines[s:e]
    # Show line numbers
    numbered = "".join(
        f"{i + 1:>6}|{line}"
        for i, line in enumerate(selected, start=s + 1)
    )

    output = f"File: {path} ({total_lines} lines total, showing {s + 1}–{e})\n{numbered}"

    return json.dumps({
        "function": "read_file",
        "arguments": {"path": path, "start_line": start_line, "end_line": end_line},
        "result": output
    }, indent=2)


register_tool("read_file", read_file, tags=["system"])
