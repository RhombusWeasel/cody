import os
import importlib.util
import inspect
from pathlib import Path

class CommandBase:
    description: str = "Base command"

    async def execute(self, app, args: list[str]):
        raise NotImplementedError("Subclasses must implement execute method")

def load_commands(app_dir: str) -> dict[str, CommandBase]:
    commands = {}
    
    # Define directories to scan
    # app_dir is expected to be the root directory of the project
    dirs_to_scan = [
        os.path.join(app_dir, "components", "chat", "cmd"),
        os.path.join(app_dir, "cmd")
    ]
    
    for d in dirs_to_scan:
        if not os.path.exists(d):
            continue
            
        for filename in os.listdir(d):
            if filename.endswith(".py") and not filename.startswith("__"):
                module_name = filename[:-3]
                file_path = os.path.join(d, filename)
                
                # Dynamically load the module
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    try:
                        spec.loader.exec_module(module)
                        
                        # Find subclasses of CommandBase
                        for name, obj in inspect.getmembers(module):
                            if inspect.isclass(obj) and issubclass(obj, CommandBase) and obj is not CommandBase:
                                commands[module_name] = obj()
                                break # Only load one command per file
                    except Exception as e:
                        print(f"Failed to load command from {file_path}: {e}")
                        
    return commands
