"""Skills sidebar with file-tree view for scripts/ and components/."""
import os
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container, Vertical, VerticalScroll
from textual.widgets import Button, Label
from textual import on

from components.tree import GenericTree, NodeSelected
from components.utils.input_modal import InputModal
from utils.skills import skill_manager
from utils import fs_tree
from utils.tree_model import TreeEntry
import utils.icons as icons
from utils.editors import open_file_editor


class SkillsTree(GenericTree):
  """Skills tree with file-tree view for scripts/ and components/."""

  def __init__(self, **kwargs):
    super().__init__(icon_set=icons.SKILL_ICON_SET, **kwargs)

  def get_visible_entries(self) -> list[TreeEntry]:
    result: list[TreeEntry] = []
    skill_manager.discover_skills()
    snapshot = sorted(skill_manager.skills.keys())

    for i, skill_name in enumerate(snapshot):
      skill = skill_manager.get_skill(skill_name)
      if not skill:
        continue
      base_dir = Path(skill["base_dir"])
      skill_id = ("skill", skill_name)
      is_last_skill = i == len(snapshot) - 1
      branch = self.LAST_BRANCH if is_last_skill else self.BRANCH

      result.append(TreeEntry(
        node_id=skill_id,
        indent=branch,
        is_expandable=True,
        is_expanded=skill_id in self._expanded,
        display_name=skill_name,
        icon=self.icon("skill"),
      ))

      if skill_id not in self._expanded:
        continue

      ext = self.SPACER if is_last_skill else self.VERTICAL
      scripts_path = base_dir / "scripts"
      components_path = base_dir / "components"
      skill_file = base_dir / "SKILL.md"

      children = []
      if scripts_path.exists():
        children.append(("scripts", scripts_path))
      if components_path.exists():
        children.append(("components", components_path))
      children.append(("edit_skill", skill_file))

      for j, (label, path_or_edit) in enumerate(children):
        is_last_child = j == len(children) - 1
        child_branch = self.LAST_BRANCH if is_last_child else self.BRANCH
        child_ext = self.SPACER if is_last_child else self.VERTICAL

        if label == "edit_skill":
          result.append(TreeEntry(
            node_id={"kind": "edit_skill", "path": str(path_or_edit)},
            indent=ext + child_branch,
            is_expandable=False,
            is_expanded=False,
            display_name="Edit SKILL.md",
            icon=self.icon("file"),
          ))
        else:
          path = path_or_edit
          is_expanded = path in self._expanded
          result.append(TreeEntry(
            node_id=path,
            indent=ext + child_branch,
            is_expandable=True,
            is_expanded=is_expanded,
            display_name=path.name + "/",
            icon=self.icon("folder"),
          ))
          if is_expanded:
            fs_tree.path_entries_to_tree(
              result, path, ext + child_ext, self._expanded,
              self.BRANCH, self.LAST_BRANCH, self.VERTICAL, self.SPACER,
              folder_icon=self.icon("folder"), file_icon=self.icon("file"), file_icons=icons.FILE_ICONS,
            )

    return result

  def get_node_buttons(self, node_id, is_expandable) -> list[Button]:
    return []



class ToolList(Container):

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self._last_snapshot = None

  def compose(self) -> ComposeResult:
    with Vertical():
      yield Label(f"{icons.SKILLS}  Skills", classes="header")
      with VerticalScroll():
        yield SkillsTree(id="skills_tree")
      yield Button("Add Skill", id="add_skill_btn", variant="primary")

  def on_mount(self) -> None:
    self._refresh_tree(force=True)
    self.set_interval(2, lambda: self._refresh_tree())

  def _refresh_tree(self, force: bool = False) -> None:
    skill_manager.discover_skills()
    snapshot = sorted(skill_manager.skills.keys())
    if not force and snapshot == self._last_snapshot:
      return
    self._last_snapshot = snapshot
    tree = self.query_one("#skills_tree", SkillsTree)
    tree.reload()

  @on(NodeSelected)
  def on_skill_node_selected(self, event: NodeSelected) -> None:
    node_id = event.node_id
    if isinstance(node_id, dict):
      if node_id.get("kind") == "edit_skill":
        path = node_id.get("path")
        if path and os.path.exists(path):
          self._open_skill_editor(path)
      return
    if isinstance(node_id, Path) and node_id.is_file():
      self._open_file_editor(node_id)

  def _open_skill_editor(self, path: str) -> None:
    with open(path, "r", encoding="utf-8") as f:
      content = f.read()

    def save_skill(new_content: str | None) -> None:
      if new_content is not None:
        with open(path, "w", encoding="utf-8") as f:
          f.write(new_content)
        self.app.notify(f"Saved {path}")
        self._refresh_tree(force=True)

    self.app.push_screen(
      InputModal(
        f"Edit {os.path.basename(path)}",
        initial_value=content,
        multiline=True,
        language="markdown",
        code_editor=True,
      ),
      save_skill,
    )

  def _open_file_editor(self, path: Path) -> None:
    open_file_editor(self.app, path, on_saved=lambda: self._refresh_tree(force=True))

  @on(Button.Pressed, "#add_skill_btn")
  def on_add_skill(self) -> None:
    def check_name(name: str | None) -> None:
      if not name or not name.strip():
        return
      name = name.strip()
      project_dir = Path(os.getcwd())
      skill_dir = project_dir / ".agents" / "skills" / name
      skill_dir.mkdir(parents=True, exist_ok=True)
      skill_file = skill_dir / "SKILL.md"
      if not skill_file.exists():
        with open(skill_file, "w", encoding="utf-8") as f:
          f.write(f"---\nname: {name}\ndescription: Description for {name}\n---\n\n# {name}\n\nAdd skill instructions here.\n")
        self.app.notify(f"Created skill '{name}' at {skill_file}")
        self._refresh_tree(force=True)
      else:
        self.app.notify(f"Skill '{name}' already exists!", severity="error")

    self.app.push_screen(InputModal("Enter new skill name:"), check_name)
