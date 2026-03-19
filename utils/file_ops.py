"""Shared file-operation buttons and action handling for tree components."""
from pathlib import Path
from typing import Callable

from textual.widgets import Button

from utils import fs_tree
from utils.icons import DELETE, NEW_FILE, NEW_FOLDER
from utils.editors import open_file_editor
from components.utils.input_modal import InputModal


def node_buttons(is_expandable: bool, make_btn: Callable) -> list[Button]:
  """Return action buttons for a tree node.

  Args:
    is_expandable: True for folders, False for files.
    make_btn: The tree's _make_btn(label, tooltip, action) factory.
  """
  if is_expandable:
    return [
      make_btn(NEW_FILE, "New file", "new_file"),
      make_btn(NEW_FOLDER, "New folder", "new_dir"),
      make_btn(DELETE, "Delete", "delete"),
    ]
  return [make_btn(DELETE, "Delete", "delete")]


def handle_action(app, path: Path, action: str, on_refresh: Callable) -> None:
  """Handle a file-tree button action with modal prompts.

  Args:
    app: The Textual app instance.
    path: The filesystem path the action targets.
    action: One of 'edit', 'delete', 'new_file', 'new_dir'.
    on_refresh: Called after a successful operation to reload the tree.
  """
  if action == "edit":
    open_file_editor(app, path, on_saved=on_refresh)

  elif action == "delete":
    def on_confirm(ok: bool | None):
      if ok and fs_tree.delete_path(path):
        app.notify(f"Deleted {path.name}")
        on_refresh()
      elif ok:
        app.notify("Delete failed", severity="error")
    app.push_screen(
      InputModal(f"Delete {path.name}?", initial_value="", confirm_only=True),
      on_confirm,
    )

  elif action == "new_file":
    def on_file_name(name: str | None):
      if name and name.strip():
        new_path = path / name.strip()
        if fs_tree.create_file(new_path):
          app.notify(f"Created {name.strip()}")
          on_refresh()
        else:
          app.notify("Create failed", severity="error")
    app.push_screen(InputModal("New file name", initial_value=""), on_file_name)

  elif action == "new_dir":
    def on_dir_name(name: str | None):
      if name and name.strip():
        new_path = path / name.strip()
        if fs_tree.create_dir(new_path):
          app.notify(f"Created {name.strip()}")
          on_refresh()
        else:
          app.notify("Create failed", severity="error")
    app.push_screen(InputModal("New folder name", initial_value=""), on_dir_name)
