"""Flat file tree - one row per visible entry, no nesting."""
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Button
from textual import on

from components.tree import GenericTree, NodeSelected
from components.input_modal import InputModal
from utils.cfg_man import cfg
from utils import fs_tree
from utils.tree_model import TreeEntry
from utils.icons import DELETE, NEW_FILE, NEW_FOLDER, FILE_ICONS
from utils.editors import open_file_editor


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
    if is_expandable:
      btns = [
        self._make_btn(NEW_FILE, "New file", "new_file"),
        self._make_btn(NEW_FOLDER, "New folder", "new_dir"),
        self._make_btn(DELETE, "Delete", "delete"),
      ]
    else:
      btns = [self._make_btn(DELETE, "Delete", "delete")]
    return btns

  def on_button_action(self, node_id: Path, action: str) -> None:
    if action == "edit":
      self._do_edit(node_id)
    elif action == "delete":
      self._do_delete(node_id)
    elif action == "new_file":
      self._do_new_file(node_id)
    elif action == "new_dir":
      self._do_new_dir(node_id)

  def _do_edit(self, path: Path) -> None:
    open_file_editor(self.app, path, on_saved=lambda: self._refresh())

  def _do_delete(self, path: Path) -> None:
    def on_confirm(ok: bool | None):
      if ok and fs_tree.delete_path(path):
        self.notify(f"Deleted {path.name}")
        self._expanded.discard(path)
        self._refresh()
      elif ok:
        self.notify("Delete failed", severity="error")

    self.app.push_screen(
      InputModal(f"Delete {path.name}?", initial_value="", confirm_only=True),
      on_confirm,
    )

  def _do_new_file(self, parent: Path) -> None:
    def on_result(name: str | None):
      if name and name.strip():
        new_path = parent / name.strip()
        if fs_tree.create_file(new_path):
          self.notify(f"Created {name}")
          self._refresh()
        else:
          self.notify("Create failed", severity="error")

    self.app.push_screen(InputModal("New file name", initial_value=""), on_result)

  def _do_new_dir(self, parent: Path) -> None:
    def on_result(name: str | None):
      if name and name.strip():
        new_path = parent / name.strip()
        if fs_tree.create_dir(new_path):
          self.notify(f"Created {name}")
          self._refresh()
        else:
          self.notify("Create failed", severity="error")

    self.app.push_screen(InputModal("New folder name", initial_value=""), on_result)


class FileTreeTab(Vertical):
  """Tab containing the file tree."""

  DEFAULT_CSS = """
  FileTreeTab {
    height: 100%;
    width: 100%;
  }

  #fs_tree_container {
    height: 1fr;
  }
  """

  def compose(self) -> ComposeResult:
    working_dir = Path(cfg.get("session.working_directory", "."))
    with VerticalScroll(id="fs_tree_container"):
      yield FileTree(working_dir, id="fs_file_tree")

  @on(NodeSelected)
  def on_file_selected(self, event: NodeSelected) -> None:
    path = event.node_id
    if not isinstance(path, Path) or not path.is_file():
      return
    tree = self.query_one("#fs_file_tree", FileTree)
    open_file_editor(self.app, path, on_saved=lambda: tree.reload())
