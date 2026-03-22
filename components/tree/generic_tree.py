"""Generic flat tree - one row per visible entry."""
from typing import Any

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import Button
from textual import on

from components.tree.tree_row import TreeRow, NodeToggled, NodeSelected
from utils.tree_model import TreeEntry
from utils.icons import DEFAULT_ICON_SET, FILE


class GenericTree(Vertical):
  """Flat tree - single Vertical with one row per entry. Subclass and override."""


  BRANCH = "├── "
  LAST_BRANCH = "└── "
  VERTICAL = "│   "
  SPACER = "    "

  def __init__(self, root_node_id: Any | None = None, icon_set: dict[str, str] | None = None, **kwargs):
    super().__init__(**kwargs)
    self._expanded: set[Any] = set()
    self._rows_container: Vertical | None = None
    self._root_node_id = root_node_id
    self._icon_set = {**DEFAULT_ICON_SET, **(icon_set or {})}

  def icon(self, key: str) -> str:
    """Return icon for key from this tree's icon set. Falls back to file icon."""
    return self._icon_set.get(key, FILE)

  def compose(self) -> ComposeResult:
    self._rows_container = Vertical(classes="tree_rows")
    yield self._rows_container

  def on_mount(self) -> None:
    self._refresh()

  def get_visible_entries(self) -> list[TreeEntry]:
    """Override: return list of TreeEntry for visible rows."""
    raise NotImplementedError

  def get_node_buttons(self, node_id: Any, is_expandable: bool) -> list[Button]:
    """Override: return buttons for a node."""
    raise NotImplementedError

  async def load_children_async(self, node_id: Any) -> None:
    """Override for lazy loading. Called before refresh when expanding."""
    pass

  def on_node_toggled(self, node_id: Any) -> None:
    """Override: handle expand/collapse. Default toggles _expanded and refreshes."""
    if self._root_node_id is not None and node_id == self._root_node_id:
      return
    if node_id in self._expanded:
      self._expanded.discard(node_id)
    else:
      self._expanded.add(node_id)
    self._refresh()

  def on_node_selected(self, node_id: Any) -> None:
    """Override: handle leaf selection."""
    pass

  def on_button_action(self, node_id: Any, action: str) -> None:
    """Override: handle button press."""
    pass

  def reload(self) -> None:
    """Reload tree from data. Call after external data changes."""
    self._refresh()

  def create_row_widget(self, entry: TreeEntry) -> Widget:
    """Override to use custom row widgets (e.g. vault secret rows)."""
    return TreeRow(
      node_id=entry.node_id,
      indent=entry.indent,
      is_expandable=entry.is_expandable,
      is_expanded=entry.is_expanded,
      display_name=entry.display_name,
      icon=entry.icon,
      display_rich=entry.display_rich,
      button_factory=lambda nid, exp: self._get_buttons_for_entry(nid, exp),
    )

  def _refresh(self) -> None:
    if not self._rows_container:
      return
    for child in list(self._rows_container.children):
      child.remove()
    for entry in self.get_visible_entries():
      row = self.create_row_widget(entry)
      self._rows_container.mount(row)

  def _get_buttons_for_entry(self, node_id: Any, is_expandable: bool) -> list[Button]:
    btns = self.get_node_buttons(node_id, is_expandable)
    for btn in btns:
      setattr(btn, "node_id", node_id)
    return btns

  @on(NodeToggled)
  async def _on_node_toggled(self, event: NodeToggled) -> None:
    node_id = event.node_id
    if node_id not in self._expanded:
      await self.load_children_async(node_id)
    self.on_node_toggled(node_id)

  @on(NodeSelected)
  def _on_node_selected(self, event: NodeSelected) -> None:
    self.on_node_selected(event.node_id)
