import json
import subprocess
import os
from utils.tool import register_tool

def run_command(command: str, cwd: str = None):
    """
    Executes a shell command. Use this to run scripts bundled in skills.
    Args:
        command: The shell command to execute.
        cwd: Optional working directory for the command. Defaults to current directory.
    Returns:
        A JSON string containing the tool call details and the command output (stdout and stderr).
    """
    try:
        # Avoid inheriting a TTY on stdin (would block on hidden prompts, e.g. skill vault getpass).
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True
        )
        
        output = ""
        if result.stdout:
            output += f"STDOUT:\n{result.stdout}\n"
        if result.stderr:
            output += f"STDERR:\n{result.stderr}\n"
            
        output += f"Exit code: {result.returncode}"
        
    except Exception as e:
        output = f"Error executing command: {str(e)}"

    return json.dumps({
        "function": "run_command",
        "arguments": {
            "command": command,
            "cwd": cwd
        },
        "result": output
    }, indent=2)

register_tool('run_command', run_command, tags=['system'])
