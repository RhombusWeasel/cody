import json, os

def deep_update(d, u):
    for k, v in u.items():
        if isinstance(v, dict):
            d[k] = deep_update(d.get(k, {}), v)
        else:
            d[k] = v
    return d

class Config:
    def __init__(self, base_path=None, local_path="config.json"):
        self.base_path = base_path
        self.local_path = local_path
        self.data = {}
 

        if self.base_path and os.path.exists(self.base_path):
            with open(self.base_path) as file:
                try:
                    base_data = json.loads(file.read())
                    deep_update(self.data, base_data)
                except json.JSONDecodeError:
                    pass
        elif os.path.exists(self.local_path):
            with open(self.local_path) as file:
                try:
                    local_data = json.loads(file.read())
                    deep_update(self.data, local_data)
                except json.JSONDecodeError:
                    # Wail like a banshee and quit
                    print(f"Error loading local config file {self.local_path}: {e}")
                    exit(1)
        else:
            print(f"No config file found at {self.base_path} or {self.local_path} Have you created it from the template?")
            exit(1)

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
        self.save()

    def save(self):
        if not self.local_path:
            return
        local_dir = os.path.dirname(self.local_path)
        if local_dir:
            os.makedirs(local_dir, exist_ok=True)
        with open(self.local_path, 'w') as file:
            file.write(json.dumps(self.data, indent=2))

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_base_path = f'{os.path.expanduser("~")}/.agents/cody_settings.json'
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

cfg = Config(base_path=_base_path, local_path=_local_path)
