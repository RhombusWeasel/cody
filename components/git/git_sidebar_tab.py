"""Git viewer sidebar tab with tree layout."""
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal, VerticalScroll
from textual.widgets import Button, Tree, Label
from textual import on

from components.input_modal import InputModal
from components.git.diff_modal import DiffModal
from utils.agent import TaskAgent
from utils.cfg_man import cfg
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

  def _get_working_dir(self) -> str:
    return cfg.get("session.working_directory", ".")

  def compose(self) -> ComposeResult:
    with Horizontal(id="git_buttons"):
      yield Button("Refresh", id="btn_git_refresh", variant="primary")
      yield Button("Commit", id="btn_git_commit", classes="git-icon-btn")
      yield Button("Stage", id="btn_git_stage", classes="git-icon-btn")
      yield Button("Unstage", id="btn_git_unstage", classes="git-icon-btn")
      yield Button("Checkout", id="btn_git_checkout", classes="git-icon-btn")
    with VerticalScroll(id="git_tree_container"):
      yield Label("Select an item", id="git_selected_label")
      tree = Tree("Git", id="git_tree")
      tree.root.expand()
      yield tree

  def on_mount(self) -> None:
    self._refresh_tree()
    self.query_one("#btn_git_refresh").tooltip = "Refresh"
    self.query_one("#btn_git_commit").tooltip = "Commit staged"
    self.query_one("#btn_git_stage").tooltip = "Stage selected"
    self.query_one("#btn_git_unstage").tooltip = "Unstage selected"
    self.query_one("#btn_git_checkout").tooltip = "Checkout branch"

  def _refresh_tree(self) -> None:
    tree = self.query_one("#git_tree", Tree)
    tree.clear()
    wd = self._get_working_dir()

    if not git_viewer.get_branches(wd) and not git_viewer.get_status(wd):
      tree.root.add_leaf("Not a git repository", data={"type": "empty"})
      return

    branches = git_viewer.get_branches(wd)
    branches_node = tree.root.add("Branches", data={"type": "category", "category": "branches"}, expand=True)
    if not branches:
      branches_node.add_leaf("(no commits yet)", data={"type": "empty"})
    else:
      for b in branches:
        label = f"{b['name']} *" if b["is_current"] else b["name"]
        branches_node.add_leaf(label, data={"type": "branch", "name": b["name"], "is_current": b["is_current"]})

    status_list = git_viewer.get_status(wd)
    changes_node = tree.root.add("Changes", data={"type": "category", "category": "changes"}, expand=True)
    if not status_list:
      changes_node.add_leaf("(clean)", data={"type": "empty"})
    else:
      for s in status_list:
        prefix = "[staged] " if s["staged"] else ""
        label = f"{prefix}{s['status']} {s['path']}"
        changes_node.add_leaf(label, data={"type": "change", "path": s["path"], "staged": s["staged"]})

    commits = git_viewer.get_commits(wd, 15)
    commits_node = tree.root.add("Recent Commits", data={"type": "category", "category": "commits"}, expand=True)
    if not commits:
      commits_node.add_leaf("(none)", data={"type": "empty"})
    else:
      for c in commits:
        label = f"{c['hash']} {c['message'][:40]}"
        commits_node.add_leaf(label, data={"type": "commit", "hash": c["full_hash"], "short": c["hash"], "message": c["message"]})

  @on(Tree.NodeSelected, "#git_tree")
  def on_node_selected(self, event) -> None:
    node = event.node
    self.selected_node_data = node.data if node.data else None
    label = self.query_one("#git_selected_label", Label)
    if not self.selected_node_data:
      label.update("Select an item")
      return
    t = self.selected_node_data.get("type")
    if t == "branch":
      label.update(f"Branch: {self.selected_node_data['name']}")
    elif t == "change":
      label.update(f"File: {self.selected_node_data['path']}")
      self._handle_show_diff()
    elif t == "commit":
      label.update(f"Commit: {self.selected_node_data['short']}")
      self._handle_show_diff()
    else:
      label.update("Select an item")

  @on(Tree.NodeExpanded, "#git_tree")
  def on_node_expanded(self, event) -> None:
    pass

  def _show_diff(self, title: str, content: str, file_path: str | None = None) -> None:
    self.app.push_screen(DiffModal(title, content, file_path=file_path))

  @on(Button.Pressed, "#btn_git_refresh")
  def on_refresh(self) -> None:
    self._refresh_tree()

  @on(Button.Pressed, "#btn_git_commit")
  def on_commit(self) -> None:
    wd = self._get_working_dir()
    if not git_viewer.get_branches(wd):
      self.app.notify("Not a git repository", severity="warning")
      return
    self.run_worker(self._generate_and_show_commit_modal(wd))

  async def _generate_and_show_commit_modal(self, wd: str) -> None:
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
          self._refresh_tree()
        else:
          self.app.notify("Nothing to commit or commit failed", severity="warning")

    self.app.push_screen(InputModal("Commit message", initial_value=initial, multiline=True), do_commit)

  @on(Button.Pressed, "#btn_git_stage")
  def on_stage(self) -> None:
    wd = self._get_working_dir()
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
    wd = self._get_working_dir()
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
    wd = self._get_working_dir()
    if data and data.get("type") == "branch":
      name = data["name"]
      if data.get("is_current"):
        self.app.notify(f"Already on {name}", severity="information")
        return
      if git_viewer.checkout_branch(wd, name):
        self.app.notify(f"Switched to {name}")
        self._refresh_tree()
      else:
        self.app.notify("Checkout failed", severity="error")
    else:
      self.app.notify("Select a branch to checkout", severity="warning")

  def _handle_show_diff(self) -> None:
    data = self.selected_node_data
    wd = self._get_working_dir()
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
