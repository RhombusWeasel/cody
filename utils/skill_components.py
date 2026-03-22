import importlib.util
import sys
from pathlib import Path

from utils.skills import skill_manager


def _get_widget_factory(module):
  if hasattr(module, 'get_sidebar_widget'):
    return module.get_sidebar_widget
  if hasattr(module, 'SidebarWidget'):
    cls = module.SidebarWidget
    return lambda: cls()
  return None


def discover_sidebar_tabs():
  """
  Scans enabled skills for components/sidebar_tab.py.
  Returns list of (tab_id, label, widget_factory, tooltip).
  tooltip comes from sidebar_tooltip if set, else label.
  """
  result = []
  skill_manager.discover_skills()

  for name, skill in skill_manager.skills.items():
    base_dir = Path(skill['base_dir'])
    sidebar_module_path = base_dir / 'components' / 'sidebar_tab.py'
    if not sidebar_module_path.exists():
      continue

    inserted_paths: list[str] = []
    for sub in ('components', 'scripts'):
      p = base_dir / sub
      if p.exists():
        s = str(p)
        if s not in sys.path:
          sys.path.append(s)
          inserted_paths.append(s)
    try:
      mod_name = f"skill_components_{name.replace('-', '_')}"
      spec = importlib.util.spec_from_file_location(mod_name, sidebar_module_path)
      if not spec or not spec.loader:
        continue
      module = importlib.util.module_from_spec(spec)
      spec.loader.exec_module(module)

      label = getattr(module, 'sidebar_label', None)
      if not label or not isinstance(label, str):
        continue

      factory = _get_widget_factory(module)
      if not factory:
        continue

      tooltip = getattr(module, 'sidebar_tooltip', None)
      if not tooltip or not isinstance(tooltip, str):
        tooltip = label

      safe_name = name.replace(' ', '-').replace('_', '-')
      tab_id = f"tab-skill-{safe_name}"
      result.append((tab_id, label, factory, tooltip))
    except Exception as e:
      print(f"Error loading skill sidebar component {name}: {e}")
    finally:
      for s in inserted_paths:
        if s in sys.path:
          sys.path.remove(s)

  return result
