import json
import os
from utils.tool import register_tool


def write_file(path: str, lines: list = None):
    """
    Write content to a file, creating parent directories as needed.

    Provide `lines` as a JSON array of strings (e.g. ["line1", "line2"]).
    When calling this tool, the `lines` parameter MUST be passed with
    string="false" so it is interpreted as a JSON array, not a string.
    If passed as a string (string="true"), the tool will attempt to parse
    it as JSON automatically as a fallback.

    This is the preferred method for writing files; do not use shell
    commands to write data unless that is the specific request.

    Args:
        path: Path to the file to write (creates or overwrites).
        lines: List of strings to write (joined with newlines). Pass as a
               JSON array with string="false".
    Returns:
        A JSON string confirming the write or describing an error.
    """
    if isinstance(lines, str):
        # Fallback: try to parse a JSON-encoded string (e.g. when an agent
        # mistakenly passes string="true" for the list parameter).
        try:
            parsed = json.loads(lines)
            if isinstance(parsed, list):
                lines = parsed
            else:
                return json.dumps({
                    "function": "write_file",
                    "arguments": {"path": path},
                    "result": "Error: 'lines' must be a JSON array of strings (e.g. [\"line1\", \"line2\"]). Pass with string=\"false\"."
                }, indent=2)
        except json.JSONDecodeError:
            return json.dumps({
                "function": "write_file",
                "arguments": {"path": path},
                "result": "Error: 'lines' must be a JSON array of strings (e.g. [\"line1\", \"line2\"]). Pass with string=\"false\"."
            }, indent=2)

    if isinstance(lines, list):
        body = "\n".join(lines)
    else:
        return json.dumps({
            "function": "write_file",
            "arguments": {"path": path},
            "result": "Error: provide 'lines' (list of str). Pass as a JSON array with string=\"false\"."
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