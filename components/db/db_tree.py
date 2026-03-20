"""Database tree - connections, tables, views, triggers."""
from typing import Any, Callable

from textual.widgets import Button

from components.tree import GenericTree
from utils.tree_model import TreeEntry
from utils.db import db_manager
from utils.icons import DB_ICON_SET, DELETE, REFRESH


ROOT_ID = "root"
CATEGORIES = ["table", "view", "trigger"]


class DBTree(GenericTree):
  """Tree of database connections with Tables/Views/Triggers."""

  def __init__(self, on_select: Callable[[str], None] | None = None, icon_set: dict | None = None, **kwargs):
    super().__init__(root_node_id=ROOT_ID, icon_set=icon_set or DB_ICON_SET, **kwargs)
    self._on_select_callback = on_select
    self._child_cache: dict[tuple[str, str], list[str]] = {}

  def get_visible_entries(self) -> list[TreeEntry]:
    result: list[TreeEntry] = []
    self._expanded.add(ROOT_ID)

    result.append(TreeEntry(
      node_id=ROOT_ID,
      indent="",
      is_expandable=True,
      is_expanded=ROOT_ID in self._expanded,
      display_name="Databases",
      icon=self.icon("database"),
    ))

    conn_paths = list(db_manager.connections.keys())
    for i, path in enumerate(conn_paths):
      is_last_conn = i == len(conn_paths) - 1
      branch = self.LAST_BRANCH if is_last_conn else self.BRANCH
      result.append(TreeEntry(
        node_id=path,
        indent=branch,
        is_expandable=True,
        is_expanded=path in self._expanded,
        display_name=db_manager.get_label(path),
        icon=self.icon("database"),
      ))

      if path in self._expanded:
        ext = self.SPACER if is_last_conn else self.VERTICAL
        for j, cat in enumerate(CATEGORIES):
          cat_id = (path, cat)
          is_last_cat = j == len(CATEGORIES) - 1
          cat_branch = self.LAST_BRANCH if is_last_cat else self.BRANCH
          result.append(TreeEntry(
            node_id=cat_id,
            indent=ext + cat_branch,
            is_expandable=True,
            is_expanded=cat_id in self._expanded,
            display_name=cat.title() + "s",
            icon=self.icon("folder"),
          ))

          if cat_id in self._expanded:
            cat_ext = self.SPACER if is_last_cat else self.VERTICAL
            names = self._child_cache.get(cat_id, [])
            for k, name in enumerate(names):
              is_last_item = k == len(names) - 1
              item_branch = self.LAST_BRANCH if is_last_item else self.BRANCH
              item_id = (path, cat, name)
              cat_icon = self.icon(cat) if cat in ("table", "view", "trigger") else self.icon("file")
              result.append(TreeEntry(
                node_id=item_id,
                indent=ext + cat_ext + item_branch,
                is_expandable=False,
                is_expanded=False,
                display_name=name,
                icon=cat_icon,
              ))

    return result

  def get_node_buttons(self, node_id: Any, is_expandable: bool) -> list[Button]:
    from components.utils.buttons import RefreshButton, DeleteButton
    if node_id == ROOT_ID:
      return []
    if isinstance(node_id, str):
      return [
        RefreshButton(action=lambda n=node_id: self.on_button_action(n, "refresh"), tooltip="Refresh schema"),
        DeleteButton(action=lambda n=node_id: self.on_button_action(n, "remove"), tooltip="Remove connection"),
      ]
    if isinstance(node_id, tuple) and len(node_id) == 2:
      return []
    return []

  async def load_children_async(self, node_id: Any) -> None:
    if isinstance(node_id, tuple) and len(node_id) == 2:
      path, category = node_id
      if path not in db_manager.connections:
        return
      try:
        names = await db_manager.list_schema_objects(path, category)
        self._child_cache[node_id] = names if names else ["None found"]
      except Exception as e:
        self._child_cache[node_id] = [f"Error: {e}"]

  def on_node_toggled(self, node_id: Any) -> None:
    super().on_node_toggled(node_id)
    path = node_id if isinstance(node_id, str) else (node_id[0] if isinstance(node_id, tuple) else None)
    if path and self._on_select_callback:
      self._on_select_callback(path)

  def on_node_selected(self, node_id: Any) -> None:
    path = None
    if isinstance(node_id, str) and node_id != ROOT_ID:
      path = node_id
    elif isinstance(node_id, tuple) and len(node_id) >= 2:
      path = node_id[0]
    if path and self._on_select_callback:
      self._on_select_callback(path)

  def on_button_action(self, node_id: Any, action: str) -> None:
    if action == "remove" and isinstance(node_id, str):
      db_manager.remove_connection(node_id)
      self._expanded.discard(node_id)
      self._child_cache = {k: v for k, v in self._child_cache.items() if k[0] != node_id}
      self.reload()
    elif action == "refresh" and isinstance(node_id, str):
      self._child_cache = {k: v for k, v in self._child_cache.items() if k[0] != node_id}
      self._expanded.discard(node_id)
      self.reload()
