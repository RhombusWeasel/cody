"""Git viewer sidebar tab."""
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal, VerticalScroll
from textual.widgets import Button, Label
from textual import on

from components.tree import NodeSelected
from components.input_modal import InputModal
from components.git.diff_modal import DiffModal
from components.git.git_tree import GitTree, SelectionChanged, _get_working_dir
from utils.agent import TaskAgent
from utils import git_viewer

COMMIT_MSG_PROMPT = """You generate conventional git commit messages. Output only the message, no preamble.
Format: type(scope): subject. Types: feat, fix, docs, style, refactor, test, chore.
Keep subject under 50 chars. Add a blank line and body for context if helpful."""


class GitSidebarTab(Vertical):
  DEFAULT_CSS = """
  GitSidebarTab {
    height: 100%;
    width: 100%;
  }

  #git_buttons {
    height: auto;
    width: 100%;
    margin-bottom: 1;
  }

  #git_tree_container {
    height: 1fr;
  }

  .git-icon-btn {
    min-width: 5;
    width: auto;
    height: 1;
    border: round $secondary;
    background: $secondary;
  }

  #git_selected_label {
    text-style: bold;
    margin-bottom: 1;
    color: $success;
    height: auto;
  }
  """

  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self.selected_node_data = None
    self.selected_for_action: set[str] = set()

  def compose(self) -> ComposeResult:
    with Horizontal(id="git_buttons"):
      yield Button("Refresh", id="btn_git_refresh", variant="primary")
      yield Button("Commit", id="btn_git_commit", classes="git-icon-btn")
      yield Button("Stage", id="btn_git_stage", classes="git-icon-btn")
      yield Button("Unstage", id="btn_git_unstage", classes="git-icon-btn")
      yield Button("Checkout", id="btn_git_checkout", classes="git-icon-btn")
    with VerticalScroll(id="git_tree_container"):
      yield Label("Select an item", id="git_selected_label")
      yield GitTree(id="git_tree", selected_for_action=self.selected_for_action)

  def on_mount(self) -> None:
    self.query_one("#btn_git_refresh").tooltip = "Refresh"
    self.query_one("#btn_git_commit").tooltip = "Commit staged"
    self.query_one("#btn_git_stage").tooltip = "Stage selected"
    self.query_one("#btn_git_unstage").tooltip = "Unstage selected"
    self.query_one("#btn_git_checkout").tooltip = "Checkout branch"

  def _refresh_tree(self) -> None:
    tree = self.query_one("#git_tree", GitTree)
    tree.reload()

  def _update_label(self) -> None:
    label = self.query_one("#git_selected_label", Label)
    n = len(self.selected_for_action)
    sel = f"{n} file(s) selected" if n else ""
    if not self.selected_node_data:
      label.update(sel or "Select an item")
      return
    t = self.selected_node_data.get("type")
    if t == "branch":
      label.update(f"Branch: {self.selected_node_data['name']}" + (f" | {sel}" if sel else ""))
    elif t == "change":
      label.update(f"File: {self.selected_node_data['path']}" + (f" | {sel}" if sel else ""))
    elif t == "commit":
      label.update(f"Commit: {self.selected_node_data['short']}" + (f" | {sel}" if sel else ""))
    else:
      label.update(sel or "Select an item")

  @on(NodeSelected)
  def on_git_node_selected(self, event: NodeSelected) -> None:
    self.selected_node_data = event.node_id if isinstance(event.node_id, dict) else None
    self._update_label()
    if self.selected_node_data and self.selected_node_data.get("type") in ("change", "commit"):
      self._handle_show_diff()

  @on(SelectionChanged)
  def on_selection_changed(self) -> None:
    self._update_label()

  def _show_diff(self, title: str, content: str, file_path: str | None = None) -> None:
    self.app.push_screen(DiffModal(title, content, file_path=file_path))

  @on(Button.Pressed, "#btn_git_refresh")
  def on_refresh(self) -> None:
    self._refresh_tree()

  @on(Button.Pressed, "#btn_git_commit")
  def on_commit(self) -> None:
    wd = _get_working_dir()
    if not git_viewer.get_branches(wd):
      self.app.notify("Not a git repository", severity="warning")
      return
    self.run_worker(self._generate_and_show_commit_modal(wd))

  async def _generate_and_show_commit_modal(self, wd: str) -> None:
    if self.selected_for_action:
      for path in self.selected_for_action:
        git_viewer.stage(wd, path)
    diff = git_viewer.get_diff(wd, staged=True)
    if not diff or diff == "(no changes)":
      self.app.notify("Nothing staged to commit", severity="warning")
      return
    self.app.notify("Generating commit message...", severity="information")
    agent = TaskAgent(COMMIT_MSG_PROMPT, tools=[])
    msg = await agent.run(f"Generate a commit message for:\n\n{diff}")
    initial = msg.strip() if msg else ""

    def do_commit(m: str | None) -> None:
      if m and m.strip():
        if git_viewer.commit(wd, m.strip()):
          self.app.notify("Committed")
          self.selected_for_action.clear()
          self._refresh_tree()
          self._update_label()
        else:
          self.app.notify("Nothing to commit or commit failed", severity="warning")

    self.app.push_screen(InputModal("Commit message", initial_value=initial, multiline=True), do_commit)

  @on(Button.Pressed, "#btn_git_stage")
  def on_stage(self) -> None:
    wd = _get_working_dir()
    if self.selected_for_action:
      ok = True
      for path in self.selected_for_action:
        if not git_viewer.stage(wd, path):
          ok = False
      if ok:
        n = len(self.selected_for_action)
        self.app.notify(f"Staged {n} file(s)")
        self._refresh_tree()
      else:
        self.app.notify("Stage failed", severity="error")
      return
    data = self.selected_node_data
    if data and data.get("type") == "change":
      path = data["path"]
      if git_viewer.stage(wd, path):
        self.app.notify(f"Staged {path}")
        self._refresh_tree()
      else:
        self.app.notify("Stage failed", severity="error")
    else:
      if git_viewer.stage(wd, None):
        self.app.notify("Staged all")
        self._refresh_tree()
      else:
        self.app.notify("Stage failed", severity="error")

  @on(Button.Pressed, "#btn_git_unstage")
  def on_unstage(self) -> None:
    wd = _get_working_dir()
    if self.selected_for_action:
      ok = True
      for path in self.selected_for_action:
        if not git_viewer.unstage(wd, path):
          ok = False
      if ok:
        n = len(self.selected_for_action)
        self.app.notify(f"Unstaged {n} file(s)")
        self._refresh_tree()
      else:
        self.app.notify("Unstage failed", severity="error")
      return
    data = self.selected_node_data
    if data and data.get("type") == "change" and data.get("staged"):
      path = data["path"]
      if git_viewer.unstage(wd, path):
        self.app.notify(f"Unstaged {path}")
        self._refresh_tree()
      else:
        self.app.notify("Unstage failed", severity="error")
    else:
      self.app.notify("Select a staged file to unstage", severity="warning")

  @on(Button.Pressed, "#btn_git_checkout")
  def on_checkout(self) -> None:
    data = self.selected_node_data
    wd = _get_working_dir()
    if data and data.get("type") == "branch":
      name = data["name"]
      if data.get("is_current"):
        self.app.notify(f"Already on {name}", severity="information")
        return
      success, err_msg = git_viewer.checkout_branch(wd, name)
      if success:
        self.app.notify(f"Switched to {name}")
        self._refresh_tree()
      else:
        self.app.notify(f"Checkout failed: {err_msg}", severity="error")
    else:
      self.app.notify("Select a branch to checkout", severity="warning")

  def _handle_show_diff(self) -> None:
    data = self.selected_node_data
    wd = _get_working_dir()
    if not data:
      self.app.notify("Select a file or commit to view diff", severity="warning")
      return
    t = data.get("type")
    if t == "change":
      staged = data.get("staged", False)
      path = data["path"]
      diff = git_viewer.get_diff(wd, path, staged=staged)
      title = f"Diff: {path} ({'staged' if staged else 'unstaged'})"
      self._show_diff(title, diff, file_path=path)
    elif t == "commit":
      diff = git_viewer.get_commit_diff(wd, data["hash"])
      title = f"Commit {data['short']}: {data['message'][:30]}"
      self._show_diff(title, diff)
    else:
      self.app.notify("Select a file or commit to view diff", severity="warning")
