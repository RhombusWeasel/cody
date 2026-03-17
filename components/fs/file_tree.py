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
from utils.icons import DELETE, NEW_FILE, NEW_FOLDER, FOLDER, FILE, FILE_ICONS


LANG_MAP = {
  ".py": "python", ".lua": "lua", ".js": "javascript", ".ts": "typescript",
  ".html": "html", ".css": "css", ".json": "json", ".md": "markdown",
  ".sh": "bash", ".yaml": "yaml", ".yml": "yaml", ".toml": "toml",
  ".rs": "rust", ".go": "go", ".c": "c", ".cpp": "cpp", ".h": "c",
  ".hpp": "cpp", ".java": "java",
}


class FileTree(GenericTree):
  """Flat file tree - single Vertical with one Horizontal row per entry."""

  DEFAULT_CSS = """
  FileTree {
    height: auto;
  }

  FileTree #tree_rows {
    height: auto;
  }
  """

  def __init__(self, path: Path, **kwargs):
    super().__init__(**kwargs)
    self._root_path = path.resolve()

  def get_visible_entries(self) -> list[TreeEntry]:
    result: list[TreeEntry] = []

    def add_children(parent: Path, prefix: str) -> None:
      entries = fs_tree.list_dir(parent)
      for i, (name, is_dir) in enumerate(entries):
        path = parent / name
        is_last = i == len(entries) - 1
        branch = self.LAST_BRANCH if is_last else self.BRANCH
        is_expanded = path in self._expanded
        icon = FOLDER if is_dir else FILE_ICONS.get(path.suffix.lower(), FILE)
        display_name = path.name or str(path)
        result.append(TreeEntry(
          node_id=path,
          indent=prefix + branch,
          is_expandable=is_dir,
          is_expanded=is_expanded,
          display_name=display_name,
          icon=icon,
        ))
        if is_dir and is_expanded:
          ext = self.SPACER if is_last else self.VERTICAL
          add_children(path, prefix + ext)

    result.append(TreeEntry(
      node_id=self._root_path,
      indent="",
      is_expandable=True,
      is_expanded=True,
      display_name=".",
      icon=FOLDER,
    ))
    add_children(self._root_path, "")
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

  def on_node_toggled(self, node_id: Path) -> None:
    if node_id == self._root_path:
      return
    super().on_node_toggled(node_id)

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
    try:
      content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
      self.notify("Not a text file", severity="warning")
      return
    except Exception as e:
      self.notify(f"Error reading: {e}", severity="error")
      return
    ext = path.suffix.lower()
    language = LANG_MAP.get(ext)
    code_editor = ext in LANG_MAP

    def on_result(new_content: str | None):
      if new_content is not None:
        try:
          path.write_text(new_content, encoding="utf-8")
          self.notify(f"Saved {path.name}")
        except Exception as e:
          self.notify(f"Error saving: {e}", severity="error")

    self.app.push_screen(
      InputModal(
        title=f"Editing {path.name}",
        initial_value=content,
        multiline=True,
        language=language,
        code_editor=bool(code_editor),
      ),
      on_result,
    )

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
    try:
      content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
      return
    except Exception as e:
      self.notify(f"Error reading file: {e}", severity="error")
      return
    ext = path.suffix.lower()
    language = LANG_MAP.get(ext)
    code_editor = ext in LANG_MAP

    def check_modal_result(new_content: str | None):
      if new_content is not None:
        try:
          path.write_text(new_content, encoding="utf-8")
          self.notify(f"Saved {path.name}")
        except Exception as e:
          self.notify(f"Error saving file: {e}", severity="error")

    self.app.push_screen(
      InputModal(
        title=f"Editing {path.name}",
        initial_value=content,
        multiline=True,
        language=language,
        code_editor=bool(code_editor),
      ),
      check_modal_result,
    )
