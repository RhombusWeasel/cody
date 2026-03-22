import ast
import os

def get_cody_dir() -> str:
    """Returns the absolute path to the Cody application directory."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_global_agents_dir() -> str:
    """Returns the absolute path to the global ~/.agents directory."""
    return os.path.join(os.path.expanduser("~"), ".agents")

def bundled_agent_definitions_dir() -> str:
    """
    Directory containing shipped sub-agent JSON definitions (skills/agents/bundled/).
    Used when seeding the agents table on first DB init.
    """
    return os.path.join(get_cody_dir(), "skills", "agents", "bundled")

def tiered_dir_templates(subpath: str) -> list[str]:
    """
    Template strings for the standard 3-tier search order (resolved via resolve_dir_templates):
    1. $CODY_DIR/{subpath}
    2. ~/.agents/{subpath}
    3. {working_directory}/.agents/{subpath}
    """
    return [
        f"$CODY_DIR/{subpath}",
        f"~/.agents/{subpath}",
        f"{{working_directory}}/.agents/{subpath}",
    ]

def resolve_dir_templates(directories: list[str], working_dir: str) -> list[str]:
    """
    Replaces $CODY_DIR, ~, and {working_directory} in custom config lists.
    """
    cody_dir = get_cody_dir()
    resolved = []
    for d in directories:
        d = d.replace('$CODY_DIR', cody_dir)
        d = d.replace('{working_directory}', working_dir)
        d = os.path.expanduser(d)
        resolved.append(d)
    return resolved

def resolved_tiered_paths(subpath: str, working_dir: str) -> list[str]:
    """Resolved absolute paths for tiered_dir_templates(subpath)."""
    return resolve_dir_templates(tiered_dir_templates(subpath), working_dir)

def get_tiered_paths(subpath: str, working_dir: str) -> list[str]:
    """
    Returns the standard 3-tier paths for a given subpath:
    1. $CODY_DIR/{subpath}
    2. ~/.agents/{subpath}
    3. {working_directory}/.agents/{subpath}
    """
    return resolved_tiered_paths(subpath, working_dir)

def parse_directory_list(raw, fallback: list[str]) -> list[str]:
    """Normalizes config values: str (optional ast list), single path, or list."""
    directories = raw
    if isinstance(directories, str):
        try:
            directories = ast.literal_eval(directories)
        except Exception:
            directories = [directories]
    if not isinstance(directories, list):
        return list(fallback)
    return directories

def default_command_directory_templates() -> list[str]:
    """
    Config template list for explicit slash-command dirs only (first → last).
    load_commands() in utils.cmd_loader also appends each enabled skill's cmd/
    directory (same tier order as skill discovery); later dirs override same name.
    """
    return ["$CODY_DIR/cmd"]

def resolved_theme_paths(working_dir: str) -> list[str]:
    """
    Theme discovery paths: standard 3-tier themes/ plus legacy ~/.agents/cody_themes
    between bundle and user themes dirs (same order as previous theme_man logic).
    """
    theme_dirs = resolved_tiered_paths("themes", working_dir)
    legacy_user_themes_dir = os.path.expanduser("~/.agents/cody_themes")
    if legacy_user_themes_dir not in theme_dirs:
        theme_dirs.insert(1, legacy_user_themes_dir)
    return theme_dirs
