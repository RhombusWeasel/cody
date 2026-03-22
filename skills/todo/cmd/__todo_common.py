"""Shared loader for todo_tools; excluded from slash command discovery (__ prefix)."""
import importlib.util
import os

_todo_mod = None


def get_todo_tools():
  global _todo_mod
  if _todo_mod is None:
    path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "tools", "todo_tools.py"))
    spec = importlib.util.spec_from_file_location("_todo_tools_dyn", path)
    _todo_mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(_todo_mod)
  return _todo_mod
