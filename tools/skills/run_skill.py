import json
import subprocess
import os
from pathlib import Path
from utils.tool import register_tool
from utils.skills import skill_manager
from utils.paths import get_cody_dir

def run_skill(skill_name: str, script_name: str, args: str = "", cwd: str = None):
    """
    Executes a script bundled within a specific skill.
    Args:
        skill_name: The name of the skill (e.g., 'coding', 'memory').
        script_name: The name of the script to run (e.g., 'read_file.py').
        args: Command line arguments to pass to the script.
        cwd: Optional working directory for the command. Defaults to current directory.
    Returns:
        A JSON string containing the tool call details and the command output.
    """
    skill = skill_manager.get_skill(skill_name)
    if not skill:
        output = f"Error: Skill '{skill_name}' not found."
        return json.dumps({
            "function": "run_skill",
            "arguments": {"skill_name": skill_name, "script_name": script_name, "args": args, "cwd": cwd},
            "result": output
        }, indent=2)

    base_dir = Path(skill['base_dir'])
    script_path = base_dir / "scripts" / script_name

    if not script_path.exists():
        output = f"Error: Script '{script_name}' not found in skill '{skill_name}' (expected at {script_path})."
        return json.dumps({
            "function": "run_skill",
            "arguments": {"skill_name": skill_name, "script_name": script_name, "args": args, "cwd": cwd},
            "result": output
        }, indent=2)

    # Determine how to run the script based on extension
    if script_path.suffix == '.py':
        command = f'python "{script_path}" {args}'
    elif script_path.suffix == '.sh':
        command = f'bash "{script_path}" {args}'
    else:
        # Fallback to just executing it directly
        command = f'"{script_path}" {args}'

    env = os.environ.copy()
    cody_dir = get_cody_dir()
    prev_pp = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = cody_dir + (os.pathsep + prev_pp if prev_pp else "")

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            env=env,
        )
        
        output = ""
        if result.stdout:
            output += f"STDOUT:\n{result.stdout}\n"
        if result.stderr:
            output += f"STDERR:\n{result.stderr}\n"
            
        output += f"Exit code: {result.returncode}"
        
    except Exception as e:
        output = f"Error executing skill script: {str(e)}"

    return json.dumps({
        "function": "run_skill",
        "arguments": {
            "skill_name": skill_name,
            "script_name": script_name,
            "args": args,
            "cwd": cwd
        },
        "result": output
    }, indent=2)

register_tool('run_skill', run_skill, tags=['skills'])
