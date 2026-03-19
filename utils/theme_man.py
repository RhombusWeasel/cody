import os
import importlib.util

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_builtin_themes_dir = os.path.join(root_dir, "themes")
_user_themes_dir = os.path.expanduser("~/.agents/cody_themes")

def discover_themes():
  themes = {}
  for themes_dir in [_builtin_themes_dir, _user_themes_dir]:
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
