import json
import subprocess
import os
from pathlib import Path
from utils.tool import register_tool
from utils.skills import skill_manager
from utils.cfg_man import cfg
from utils.paths import get_cody_dir

# Same id as skills/memory/components/memory_vault.MEMORY_VAULT_CREDENTIAL_ID
_MEMORY_VAULT_CREDENTIAL_ID = "cody_skill_memory_password"


def _inject_memory_credentials_from_unlocked_vault(env: dict) -> None:
  """Copy Reverie login from the unlocked vault into env for skill subprocesses (no shared unlock state)."""
  try:
    import utils.password_vault as password_vault
  except Exception:
    return
  cfg_u = (cfg.get("memory.username") or "").strip()
  cfg_p = (cfg.get("memory.password") or "").strip()
  vault_u = password_vault.get_credential_username(_MEMORY_VAULT_CREDENTIAL_ID)
  vault_p = password_vault.get_secret(_MEMORY_VAULT_CREDENTIAL_ID)
  out_u = vault_u or cfg_u
  out_p = vault_p or cfg_p
  if out_u:
    env["CODY_MEMORY_USERNAME"] = out_u
  if out_p:
    env["CODY_MEMORY_PASSWORD"] = out_p


def _inject_brave_search_token_from_unlocked_vault(env: dict) -> None:
  """Copy Brave Search token from unlocked vault into env for brave-search scripts."""
  try:
    from skills.brave_search.api import (
      BRAVE_SEARCH_ENV_TOKEN,
      BRAVE_SEARCH_VAULT_CREDENTIAL_ID,
      ensure_brave_search_credential_row,
    )
    import utils.password_vault as password_vault
  except Exception:
    return
  if password_vault.is_unlocked():
    ensure_brave_search_credential_row()
  token = password_vault.get_secret(BRAVE_SEARCH_VAULT_CREDENTIAL_ID)
  if token:
    env[BRAVE_SEARCH_ENV_TOKEN] = token


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

    run_cwd = cwd or cfg.get("session.working_directory") or os.getcwd()
    env = os.environ.copy()
    cody_root = str(get_cody_dir())
    prev_py = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{cody_root}{os.pathsep}{prev_py}" if prev_py else cody_root
    wd = cfg.get("session.working_directory")
    if wd:
        env["CODY_WORKING_DIRECTORY"] = wd

    if skill_name == "memory":
        _inject_memory_credentials_from_unlocked_vault(env)

    if skill_name == "brave-search":
        _inject_brave_search_token_from_unlocked_vault(env)

    try:
        # Do not inherit stdin: a TTY makes memory skill bootstrap call getpass and block forever.
        result = subprocess.run(
            command,
            shell=True,
            cwd=run_cwd,
            env=env,
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
