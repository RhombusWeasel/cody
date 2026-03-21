import os
import importlib.util
from utils.paths import resolved_theme_paths
from utils.cfg_man import cfg

def discover_themes():
  themes = {}
  working_dir = cfg.get('session.working_directory', os.getcwd())
  theme_dirs = resolved_theme_paths(working_dir)
  for themes_dir in theme_dirs:
    if not os.path.isdir(themes_dir):
      continue
    for filename in sorted(os.listdir(themes_dir)):
      if not filename.endswith(".py") or filename.startswith("_"):
        continue
      filepath = os.path.join(themes_dir, filename)
      try:
        spec = importlib.util.spec_from_file_location(filename[:-3], filepath)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "theme"):
          themes[mod.theme.name] = mod.theme
      except Exception:
        pass
  return themes
