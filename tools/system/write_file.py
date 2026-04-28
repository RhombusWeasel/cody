import json
import os
from utils.tool import register_tool


def write_file(path: str, lines: list = None):
    """
    Write content to a file, creating parent directories as needed.
    Provide `lines` (a list of strings that will be joined with newlines).
    This is the preferred method that should be used for writing files, 
    do not use shell commands to write data unless that is the request from the user.
    
    Args:
        path: Path to the file to write (creates or overwrites).
        lines: List of lines to write (joined with newlines).
    Returns:
        A JSON string confirming the write or describing an error.
    """
    if type(lines) == 'list':
        body = "\n".join(lines)
    else:
        return json.dumps({
            "function": "write_file",
            "arguments": {"path": path},
            "result": "Error: provide 'lines' (list of str)."
        }, indent=2)

    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w") as f:
            f.write(body)
    except Exception as e:
        return json.dumps({
            "function": "write_file",
            "arguments": {"path": path},
            "result": f"Error writing file: {str(e)}"
        }, indent=2)

    line_count = body.count("\n") + 1 if body else 0
    return json.dumps({
        "function": "write_file",
        "arguments": {"path": path},
        "result": f"File '{path}' written successfully ({line_count} lines)."
    }, indent=2)


register_tool("write_file", write_file, tags=["system"])
