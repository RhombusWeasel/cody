import json, os

def deep_update(d, u):
    for k, v in u.items():
        if isinstance(v, dict):
            d[k] = deep_update(d.get(k, {}), v)
        else:
            d[k] = v
    return d

class Config:
    def __init__(self, paths=None):
        self.paths = paths or []
        self.save_path = self.paths[-1] if self.paths else None
        self.data = {}
        self.changed = False
        self.load_all()

    def load_all(self):
        for path in self.paths:
            if os.path.exists(path):
                with open(path) as file:
                    try:
                        data = json.loads(file.read())
                        deep_update(self.data, data)
                    except json.JSONDecodeError as e:
                        print(f"Error loading config file {path}: {e}")

    def load_project_config(self, working_dir: str):
        project_config_path = os.path.join(working_dir, ".agents", "cody_config.json")
        if project_config_path not in self.paths:
            self.paths.append(project_config_path)
            self.save_path = project_config_path
            if os.path.exists(project_config_path):
                with open(project_config_path) as file:
                    try:
                        data = json.loads(file.read())
                        deep_update(self.data, data)
                    except json.JSONDecodeError as e:
                        print(f"Error loading project config file {project_config_path}: {e}")

    def drill(self, mod_path, default=None):
        try:
            steps = [mod_path]
            if '.' in mod_path:
                steps = mod_path.split('.')
                value = self.data
                for step in steps:
                    if isinstance(value, list) and step.isdigit():
                        value = value[int(step)]
                    else:
                        value = value[step]
                return value
            else:
                return self.data[mod_path]
        except (KeyError, TypeError, IndexError):
            return default

    def get(self, path, default=None):
        return self.drill(path, default)

    def set(self, path, value):
        steps = [path]
        if '.' in path:
            steps = path.split('.')

        target = self.data
        for i, step in enumerate(steps[:-1]):
            next_step = steps[i+1]
            if isinstance(target, list):
                if step.isdigit():
                    step = int(step)
                    while len(target) <= step:
                        target.append([] if next_step.isdigit() else {})
                    target = target[step]
                else:
                    # This shouldn't happen if paths are correct, but just in case
                    break
            else:
                if step not in target:
                    target[step] = [] if next_step.isdigit() else {}
                target = target[step]

        last_step = steps[-1]
        if isinstance(target, list):
            if last_step.isdigit():
                last_step = int(last_step)
                while len(target) <= last_step:
                    target.append(None)
                target[last_step] = value
        else:
            target[last_step] = value
        self.changed = True
        self.save()

    def save(self):
        if not self.save_path:
            return
        local_dir = os.path.dirname(self.save_path)
        if local_dir:
            os.makedirs(local_dir, exist_ok=True)
        with open(self.save_path, 'w') as file:
            file.write(json.dumps(self.data, indent=2))

from utils.paths import get_cody_dir, get_global_agents_dir
root_dir = get_cody_dir()
_base_path = os.path.join(get_global_agents_dir(), 'cody_settings.json')
_local_path = os.path.join(root_dir, ".agents", "cody_config.json")

# One-time migration from .cody to .agents
_old_base = f'{os.path.expanduser("~")}/.cody/settings.json'
_old_local = os.path.join(root_dir, "config.json")
if os.path.exists(_old_base) and not os.path.exists(_base_path):
  os.makedirs(os.path.dirname(_base_path), exist_ok=True)
  with open(_old_base) as f:
    with open(_base_path, 'w') as out:
      out.write(f.read())
if os.path.exists(_old_local) and not os.path.exists(_local_path):
  os.makedirs(os.path.dirname(_local_path), exist_ok=True)
  with open(_old_local) as f:
    with open(_local_path, 'w') as out:
      out.write(f.read())

cfg = Config(paths=[_base_path, _local_path])
