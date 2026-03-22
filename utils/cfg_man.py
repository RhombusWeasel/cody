import copy
import json
import os

def deep_update(d, u):
  for k, v in u.items():
    if isinstance(v, dict):
      d[k] = deep_update(d.get(k, {}), v)
    else:
      d[k] = v
  return d

_registered_defaults: dict = {}

def register_default_config(fragment: dict) -> None:
  deep_merge_missing(_registered_defaults, copy.deepcopy(fragment))

def deep_merge_missing(dst: dict, src: dict) -> bool:
  changed = False
  for k, v in src.items():
    if k not in dst:
      dst[k] = copy.deepcopy(v)
      changed = True
    elif isinstance(v, dict) and isinstance(dst.get(k), dict):
      if deep_merge_missing(dst[k], v):
        changed = True
  return changed

def deep_equal(a, b) -> bool:
  if type(a) is not type(b):
    return False
  if isinstance(a, dict):
    if set(a) != set(b):
      return False
    return all(deep_equal(a[k], b[k]) for k in a)
  if isinstance(a, list):
    if len(a) != len(b):
      return False
    return all(deep_equal(x, y) for x, y in zip(a, b))
  return a == b

def deep_overlay_diff(merged: dict, baseline: dict) -> dict:
  out = {}
  for k, v in merged.items():
    if k not in baseline:
      out[k] = copy.deepcopy(v)
      continue
    bv = baseline[k]
    if deep_equal(v, bv):
      continue
    if isinstance(v, dict) and isinstance(bv, dict):
      sub = deep_overlay_diff(v, bv)
      if sub:
        out[k] = sub
    else:
      out[k] = copy.deepcopy(v)
  return out

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

  def _save_path_index(self) -> int:
    if not self.save_path:
      return 0
    try:
      return self.paths.index(self.save_path)
    except ValueError:
      return len(self.paths) - 1

  def _baseline_below_save_path(self) -> dict:
    baseline = {}
    idx = self._save_path_index()
    for path in self.paths[:idx]:
      if os.path.exists(path):
        with open(path) as file:
          try:
            data = json.loads(file.read())
            deep_update(baseline, data)
          except json.JSONDecodeError as e:
            print(f"Error loading baseline config {path}: {e}")
    return baseline

  def apply_registered_defaults(self) -> bool:
    changed = deep_merge_missing(self.data, copy.deepcopy(_registered_defaults))
    if changed:
      self.save()
    return changed

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
    baseline = self._baseline_below_save_path()
    out = deep_overlay_diff(self.data, baseline)
    with open(self.save_path, 'w') as file:
      file.write(json.dumps(out, indent=2))

from utils.paths import get_cody_dir, get_global_agents_dir
root_dir = get_cody_dir()
_base_path = os.path.join(get_global_agents_dir(), 'cody_settings.json')
_local_path = os.path.join(root_dir, ".agents", "cody_config.json")

cfg = Config(paths=[_base_path, _local_path])
