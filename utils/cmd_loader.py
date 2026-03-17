import os
import importlib.util
import inspect
from pathlib import Path

from utils.cfg_man import cfg

class CommandBase:
    description: str = "Base command"

    async def execute(self, app, args: list[str]):
        raise NotImplementedError("Subclasses must implement execute method")

def _load_from_dir(commands: dict, d: str) -> None:
    """Load commands from a directory, overwriting existing entries with same name."""
    if not os.path.exists(d):
        return
    for filename in os.listdir(d):
        if filename.endswith(".py") and not filename.startswith("__"):
            module_name = filename[:-3]
            file_path = os.path.join(d, filename)
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                try:
                    spec.loader.exec_module(module)
                    for name, obj in inspect.getmembers(module):
                        if inspect.isclass(obj) and issubclass(obj, CommandBase) and obj is not CommandBase:
                            commands[module_name] = obj()
                            break
                except Exception as e:
                    print(f"Failed to load command from {file_path}: {e}")

def load_commands(app_dir: str) -> dict[str, CommandBase]:
    """
    Load commands from tiered directories. Later directories override earlier for same name.
    Uses commands.directories from config, or defaults: built-in, $CODY_DIR/cmd, ~/.agents/commands,
    {working_directory}/.agents/commands.
    """
    commands = {}
    cody_dir = app_dir
    working_dir = cfg.get('session.working_directory', os.getcwd())

    default_dirs = [
        "$CODY_DIR/components/chat/cmd",
        "$CODY_DIR/cmd",
        "~/.agents/commands",
        "{working_directory}/.agents/commands"
    ]
    directories = cfg.get('commands.directories', default_dirs)
    if isinstance(directories, str):
        try:
            import ast
            directories = ast.literal_eval(directories)
        except Exception:
            directories = [directories]
    if not isinstance(directories, list):
        directories = default_dirs

    for d in directories:
        d = d.replace('$CODY_DIR', cody_dir)
        d = d.replace('{working_directory}', working_dir)
        d = os.path.expanduser(d)
        _load_from_dir(commands, d)

    return commands
