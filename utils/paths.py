import os

def get_cody_dir() -> str:
    """Returns the absolute path to the Cody application directory."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_global_agents_dir() -> str:
    """Returns the absolute path to the global ~/.agents directory."""
    return os.path.join(os.path.expanduser("~"), ".agents")

def get_tiered_paths(subpath: str, working_dir: str) -> list[str]:
    """
    Returns the standard 3-tier paths for a given subpath:
    1. $CODY_DIR/{subpath}
    2. ~/.agents/{subpath}
    3. {working_directory}/.agents/{subpath}
    """
    return [
        os.path.join(get_cody_dir(), subpath),
        os.path.join(get_global_agents_dir(), subpath),
        os.path.join(working_dir, ".agents", subpath)
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
