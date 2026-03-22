"""Flat file tree - one row per visible entry, no nesting."""
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Button
from components.tree import GenericTree
from utils.cfg_man import cfg
from components.utils import fs_tree, file_ops
from utils.tree_model import TreeEntry
from utils.icons import FILE_ICONS


class FileTree(GenericTree):
  """Flat file tree - single Vertical with one Horizontal row per entry."""

  def __init__(self, path: Path, **kwargs):
    self._root_path = path.resolve()
    super().__init__(root_node_id=self._root_path, **kwargs)

  def get_visible_entries(self) -> list[TreeEntry]:
    result: list[TreeEntry] = []
    result.append(TreeEntry(
      node_id=self._root_path,
      indent="",
      is_expandable=True,
      is_expanded=True,
      display_name=".",
      icon=self.icon("folder"),
    ))
    fs_tree.path_entries_to_tree(
      result, self._root_path, "", self._expanded,
      self.BRANCH, self.LAST_BRANCH, self.VERTICAL, self.SPACER,
      folder_icon=self.icon("folder"), file_icon=self.icon("file"), file_icons=FILE_ICONS,
    )
    return result

  def get_node_buttons(self, node_id: Path, is_expandable: bool) -> list[Button]:
    return file_ops.node_buttons(is_expandable, lambda action: self.on_button_action(node_id, action))

  def on_button_action(self, node_id: Path, action: str) -> None:
    file_ops.handle_action(self.app, node_id, action, self._refresh)


class FileTreeTab(Vertical):
  """Tab containing the file tree."""


  def compose(self) -> ComposeResult:
    working_dir = Path(cfg.get("session.working_directory", "."))
    with VerticalScroll(id="fs_tree_container"):
      yield FileTree(working_dir, id="fs_file_tree")

