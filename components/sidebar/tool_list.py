"""Skills sidebar with file-tree view of each skill's base directory."""
import os
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container, Vertical, VerticalScroll
from textual.widgets import Button, Label
from textual import on

from components.tree import GenericTree, NodeSelected
from components.utils.input_modal import InputModal
from utils.skills import skill_manager
from components.utils import fs_tree, file_ops
from utils.tree_model import TreeEntry
from utils.editors import open_file_editor
import utils.icons as icons

class SkillsTree(GenericTree):
  """Skills tree listing the full skill folder (SKILL.md, tools/, cmd/, components/, etc.)."""

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
      if base_dir.is_dir():
        fs_tree.path_entries_to_tree(
          result, base_dir, ext, self._expanded,
          self.BRANCH, self.LAST_BRANCH, self.VERTICAL, self.SPACER,
          folder_icon=self.icon("folder"), file_icon=self.icon("file"), file_icons=icons.FILE_ICONS,
        )

    return result

  def get_node_buttons(self, node_id, is_expandable) -> list[Button]:
    if isinstance(node_id, Path):
      return file_ops.node_buttons(is_expandable, lambda action: self.on_button_action(node_id, action))
    return []

  def on_button_action(self, node_id, action: str) -> None:
    if isinstance(node_id, Path):
      file_ops.handle_action(self.app, node_id, action, self._refresh)



class ToolList(Container):

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self._last_snapshot = None

  def compose(self) -> ComposeResult:
    from components.utils.buttons import AddButton
    with Vertical():
      yield Label(f"{icons.SKILLS}  Skills", classes="header")
      with VerticalScroll():
        yield SkillsTree(id="skills_tree")
      yield AddButton(action=self.on_add_skill, label="Add Skill", id="add_skill_btn", variant="primary")

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
    if isinstance(node_id, Path) and node_id.is_file():
      open_file_editor(self.app, node_id, on_saved=lambda: self._refresh_tree(force=True))

  def on_add_skill(self) -> None:
    def check_name(name: str | None) -> None:
      if not name or not name.strip():
        return
      name = name.strip()
      from utils.cfg_man import cfg
      project_dir = Path(cfg.get('session.working_directory', os.getcwd()))
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
