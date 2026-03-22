"""Git viewer sidebar tab (skill hook)."""
import git
from textual.app import ComposeResult
from textual.containers import Vertical, Grid, VerticalScroll
from textual.widgets import Button, Label
from textual import on

from components.tree import NodeSelected
from skills.git.components.commit_message_modal import CommitMessageModal
from skills.git.components.diff_modal import DiffModal
from skills.git.components.git_tree import GitTree, SelectionChanged, _get_working_dir
from utils.agent import TaskAgent
from utils.git import stage_all, create_stash, pop_stash
import utils.icons as icons
from utils.icons import (
  GIT_COMMIT, GIT_ADD, GIT_UNSTAGE, RUN,
  GIT_STASH, GIT_POP_STASH,
)

sidebar_label = icons.GIT
sidebar_tooltip = "Git"

COMMIT_MSG_PROMPT = """You generate conventional git commit messages. Output only the message, no preamble.
Format: type(scope): subject. Types: feat, fix, docs, style, refactor, test, chore.
Keep subject under 50 chars. Add a blank line and body for context if helpful."""


class GitSidebarTab(Vertical):


  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self.selected_node_data = None
    self.selected_for_action: set[str] = set()

  def compose(self) -> ComposeResult:
    from components.utils.buttons import ActionButton, RefreshButton, RunButton
    yield Label(f"{icons.GIT} Manager", id="git_tab_title")
    with Grid(id="git_buttons"):
      yield RefreshButton(action=self.on_refresh, id="btn_git_refresh", tooltip="Refresh", classes="action-btn git-icon-btn")
      yield ActionButton(GIT_COMMIT, action=self.on_commit, id="btn_git_commit", tooltip="Commit staged", classes="action-btn git-icon-btn")
      yield ActionButton(GIT_ADD, action=self.on_stage, id="btn_git_stage", tooltip="Stage selected / all", classes="action-btn git-icon-btn")
      yield ActionButton(GIT_UNSTAGE, action=self.on_unstage, id="btn_git_unstage", tooltip="Unstage selected", classes="action-btn git-icon-btn")
      yield RunButton(action=self.on_checkout, id="btn_git_checkout", tooltip="Checkout selected branch", classes="action-btn git-icon-btn")
      yield ActionButton(GIT_STASH, action=self.on_stash, id="btn_git_stash", tooltip="Stash all changes", classes="action-btn git-icon-btn")
      yield ActionButton(GIT_POP_STASH, action=self.on_pop_stash, id="btn_git_pop_stash", tooltip="Pop latest stash", classes="action-btn git-icon-btn")
    with VerticalScroll(id="git_tree_container"):
      yield Label("Select an item", id="git_selected_label", markup=False)
      yield GitTree(id="git_tree", selected_for_action=self.selected_for_action)

  def on_mount(self) -> None:
    pass

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

  def on_refresh(self) -> None:
    self._refresh_tree()

  def on_commit(self) -> None:
    wd = _get_working_dir()
    try:
      repo = git.Repo(wd)
    except git.exc.InvalidGitRepositoryError:
      self.app.notify("Not a git repository", severity="warning")
      return

    if self.selected_for_action:
      try:
        repo.index.add(list(self.selected_for_action))
      except Exception:
        pass

    try:
      diff = repo.git.diff("--cached")
    except git.exc.GitCommandError:
      diff = ""

    if not diff:
      self.app.notify("Nothing staged to commit", severity="warning")
      return

    async def fill_ai() -> str:
      self.app.notify("Generating commit message...", severity="information")
      agent = TaskAgent(COMMIT_MSG_PROMPT, tools=[])
      msg = await agent.run(f"Generate a commit message for:\n\n{diff}")
      return (msg or "").strip()

    def do_commit(m: str | None) -> None:
      if m and m.strip():
        try:
          repo.index.commit(m.strip())
          self.app.notify("Committed")
          self.selected_for_action.clear()
          self._refresh_tree()
          self._update_label()
        except Exception:
          self.app.notify("Nothing to commit or commit failed", severity="warning")

    self.app.push_screen(
      CommitMessageModal("Commit message", staged_diff=diff, initial_value="", fill_ai=fill_ai),
      do_commit,
    )

  def on_stage(self) -> None:
    wd = _get_working_dir()
    try:
      repo = git.Repo(wd)
    except git.exc.InvalidGitRepositoryError:
      return

    if self.selected_for_action:
      try:
        repo.index.add(list(self.selected_for_action))
        n = len(self.selected_for_action)
        self.app.notify(f"Staged {n} file(s)")
        self._refresh_tree()
      except Exception:
        self.app.notify("Stage failed", severity="error")
      return

    data = self.selected_node_data
    if data and data.get("type") == "change":
      path = data["path"]
      try:
        repo.index.add([path])
        self.app.notify(f"Staged {path}")
        self._refresh_tree()
      except Exception:
        self.app.notify("Stage failed", severity="error")
    else:
      try:
        stage_all(repo)
        self.app.notify("Staged all")
        self._refresh_tree()
      except Exception:
        self.app.notify("Stage failed", severity="error")

  def on_unstage(self) -> None:
    wd = _get_working_dir()
    try:
      repo = git.Repo(wd)
    except git.exc.InvalidGitRepositoryError:
      return

    if self.selected_for_action:
      try:
        repo.head.reset(paths=list(self.selected_for_action))
        n = len(self.selected_for_action)
        self.app.notify(f"Unstaged {n} file(s)")
        self._refresh_tree()
      except Exception:
        self.app.notify("Unstage failed", severity="error")
      return

    data = self.selected_node_data
    if data and data.get("type") == "change" and data.get("staged"):
      path = data["path"]
      try:
        repo.head.reset(paths=[path])
        self.app.notify(f"Unstaged {path}")
        self._refresh_tree()
      except Exception:
        self.app.notify("Unstage failed", severity="error")
    else:
      self.app.notify("Select a staged file to unstage", severity="warning")

  def on_checkout(self) -> None:
    data = self.selected_node_data
    wd = _get_working_dir()
    try:
      repo = git.Repo(wd)
    except git.exc.InvalidGitRepositoryError:
      return

    if data and data.get("type") == "branch":
      name = data["name"]
      if data.get("is_current"):
        self.app.notify(f"Already on {name}", severity="information")
        return
      try:
        repo.heads[name].checkout()
        self.app.notify(f"Switched to {name}")
        self._refresh_tree()
      except Exception as e:
        err_msg = getattr(e, "stderr", str(e)).strip()
        self.app.notify(f"Checkout failed: {err_msg}", severity="error")
    else:
      self.app.notify("Select a branch to checkout", severity="warning")

  def on_stash(self) -> None:
    wd = _get_working_dir()
    try:
      repo = git.Repo(wd)
    except git.exc.InvalidGitRepositoryError:
      self.app.notify("Not a git repository", severity="warning")
      return
    if create_stash(repo, "WIP"):
      self.app.notify("Stashed changes")
      self._refresh_tree()
    else:
      self.app.notify("Nothing to stash", severity="warning")

  def on_pop_stash(self) -> None:
    wd = _get_working_dir()
    try:
      repo = git.Repo(wd)
    except git.exc.InvalidGitRepositoryError:
      self.app.notify("Not a git repository", severity="warning")
      return
    if pop_stash(repo, 0):
      self.app.notify("Stash applied")
      self._refresh_tree()
    else:
      self.app.notify("No stash to pop", severity="warning")

  def _handle_show_diff(self) -> None:
    data = self.selected_node_data
    wd = _get_working_dir()
    try:
      repo = git.Repo(wd)
    except git.exc.InvalidGitRepositoryError:
      return

    if not data:
      self.app.notify("Select a file or commit to view diff", severity="warning")
      return
    t = data.get("type")
    if t == "change":
      staged = data.get("staged", False)
      path = data["path"]
      try:
        if staged:
          diff = repo.git.diff("--cached", "--", path)
        else:
          diff = repo.git.diff("--", path)
        diff = diff or "(no changes)"
      except git.exc.GitCommandError as e:
        diff = str(e)
      title = f"Diff: {path} ({'staged' if staged else 'unstaged'})"
      self._show_diff(title, diff, file_path=path)
    elif t == "commit":
      try:
        diff = repo.git.show(data["hash"])
        diff = diff or "(empty)"
      except git.exc.GitCommandError as e:
        diff = str(e)
      title = f"Commit {data['short']}: {data['message'][:30]}"
      self._show_diff(title, diff)
    else:
      self.app.notify("Select a file or commit to view diff", severity="warning")


def get_sidebar_widget():
  return GitSidebarTab()
