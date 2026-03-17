from textual.widgets import Tree, Button
from textual.containers import Container, Vertical
from textual import on
import os
from pathlib import Path

from utils.skills import skill_manager
from components.input_modal import InputModal

CSS = """
ToolList {
  height: auto;
  margin: 0;
  padding: 0;
}

#add_skill_btn {
  width: 100%;
  margin-top: 1;
}
"""

class ToolList(Container):
  DEFAULT_CSS = CSS

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self._last_snapshot = None

  def compose(self):
    with Vertical():
      yield Tree("Skills")
      yield Button("Add Skill", id="add_skill_btn", variant="primary")

  def on_mount(self):
    self.update_tree(force=True)
    self.set_interval(2, self.update_tree)

  def update_tree(self, force=False):
    skill_manager.discover_skills()
    snapshot = list(skill_manager.skills.keys())
    snapshot.sort()
    
    if not force and snapshot == self._last_snapshot:
      return

    self._last_snapshot = snapshot
    tree = self.query_one(Tree)
    tree.clear()

    for skill_name in snapshot:
      skill = skill_manager.get_skill(skill_name)
      branch = tree.root.add(
        skill_name,
        data={"kind": "skill", "name": skill_name, "path": skill.get("location")}
      )
      branch.add_leaf(f"Description: {skill.get('description', 'N/A')}")
      branch.add_leaf(f"Location: {skill.get('location', 'N/A')}")
      branch.add_leaf("Edit SKILL.md", data={"kind": "edit_skill", "path": skill.get("location")})

    tree.root.expand()

  @on(Button.Pressed, "#add_skill_btn")
  def on_add_skill(self):
    def check_name(name: str | None):
      if not name:
        return
      
      name = name.strip()
      if not name:
        return
        
      # Create project-level skill
      project_dir = Path(os.getcwd())
      skill_dir = project_dir / '.agents' / 'skills' / name
      skill_dir.mkdir(parents=True, exist_ok=True)
      
      skill_file = skill_dir / 'SKILL.md'
      if not skill_file.exists():
        with open(skill_file, 'w', encoding='utf-8') as f:
          f.write(f"---\nname: {name}\ndescription: Description for {name}\n---\n\n# {name}\n\nAdd skill instructions here.\n")
        
        self.app.notify(f"Created skill '{name}' at {skill_file}")
        self.update_tree(force=True)
      else:
        self.app.notify(f"Skill '{name}' already exists!", severity="error")

    self.app.push_screen(InputModal("Enter new skill name:"), check_name)

  def on_tree_node_selected(self, event: Tree.NodeSelected):
    node = event.node
    node_data = node.data if isinstance(node.data, dict) else None
    if not node_data:
      return

    if node_data["kind"] == "skill":
      # Could open the skill file in an editor or show details
      skill_path = node_data.get("path")
    elif node_data["kind"] == "edit_skill":
      skill_path = node_data.get("path")
      if skill_path and os.path.exists(skill_path):
        with open(skill_path, 'r', encoding='utf-8') as f:
          content = f.read()
          
        def save_skill(new_content: str | None):
          if new_content is not None:
            with open(skill_path, 'w', encoding='utf-8') as f:
              f.write(new_content)
            self.app.notify(f"Saved {skill_path}")
            self.update_tree(force=True)

        self.app.push_screen(
          InputModal(
            f"Edit {os.path.basename(skill_path)}", 
            initial_value=content, 
            multiline=True, 
            language="markdown", 
            code_editor=True
          ), 
          save_skill
        )


