"""Git tree component for the sidebar."""
from typing import Any

from textual.message import Message

from components.tree import GenericTree
from components.input_modal import InputModal
from utils.cfg_man import cfg
from utils import git_viewer
from utils.tree_model import TreeEntry
from utils.icons import GIT_ICON_SET, CHECKED, UNCHECKED, SELECT_ALL, CLEAR_SELECTION, GIT_DISCARD, GIT_IGNORE, GIT_CHERRY_PICK, GIT_BRANCH, RUN, DELETE, GIT_ADD, GIT_UNSTAGE


class SelectionChanged(Message, bubble=True):
  """Posted when the selected-for-action set changes."""


def _get_working_dir() -> str:
  return cfg.get("session.working_directory", ".")


class GitTree(GenericTree):
  """Flat git tree - branches, changes, commits."""

  def __init__(self, selected_for_action: set[str] | None = None, **kwargs):
    self._selected_for_action = selected_for_action or set()
    super().__init__(icon_set=GIT_ICON_SET, **kwargs)

  def get_visible_entries(self) -> list[TreeEntry]:
    result: list[TreeEntry] = []
    wd = _get_working_dir()
    self._expanded.add(("cat", "branches"))
    self._expanded.add(("cat", "staged"))
    self._expanded.add(("cat", "changes"))
    self._expanded.add(("cat", "untracked"))
    self._expanded.add(("cat", "commits"))

    if not git_viewer.get_branches(wd) and not git_viewer.get_status(wd):
      result.append(TreeEntry(
        node_id={"type": "empty"},
        indent="",
        is_expandable=False,
        is_expanded=False,
        display_name="Not a git repository",
        icon=self.icon("git"),
      ))
      return result

    branches = git_viewer.get_branches(wd)
    result.append(TreeEntry(
      node_id=("cat", "branches"),
      indent=self.BRANCH,
      is_expandable=True,
      is_expanded=("cat", "branches") in self._expanded,
      display_name="Branches",
      icon=self.icon("folder"),
    ))
    if ("cat", "branches") in self._expanded:
      if not branches:
        result.append(TreeEntry(
          node_id={"type": "empty", "category": "branches"},
          indent=self.VERTICAL + self.LAST_BRANCH,
          is_expandable=False,
          is_expanded=False,
          display_name="(no commits yet)",
          icon=self.icon("file"),
        ))
      else:
        for i, b in enumerate(branches):
          is_last = i == len(branches) - 1
          branch = self.LAST_BRANCH if is_last else self.BRANCH
          label = f"{b['name']} *" if b["is_current"] else b["name"]
          result.append(TreeEntry(
            node_id={"type": "branch", "name": b["name"], "is_current": b["is_current"]},
            indent=self.VERTICAL + branch,
            is_expandable=False,
            is_expanded=False,
            display_name=label,
            icon=self.icon("branch"),
          ))

    status_list = git_viewer.get_status(wd)
    staged_list = [s for s in status_list if s["staged"]]
    unstaged_list = [s for s in status_list if not s["staged"] and s["status"] != "??"]
    untracked_list = [s for s in status_list if not s["staged"] and s["status"] == "??"]

    result.append(TreeEntry(
      node_id=("cat", "staged"),
      indent=self.BRANCH,
      is_expandable=True,
      is_expanded=("cat", "staged") in self._expanded,
      display_name="Staged",
      icon=self.icon("folder"),
    ))
    if ("cat", "staged") in self._expanded:
      if not staged_list:
        result.append(TreeEntry(
          node_id={"type": "empty", "category": "staged"},
          indent=self.VERTICAL + self.LAST_BRANCH,
          is_expandable=False,
          is_expanded=False,
          display_name="(none)",
          icon=self.icon("file"),
        ))
      else:
        for i, s in enumerate(staged_list):
          is_last = i == len(staged_list) - 1
          branch = self.LAST_BRANCH if is_last else self.BRANCH
          label = f"{s['status']} {s['path']}"
          result.append(TreeEntry(
            node_id={"type": "change", "path": s["path"], "staged": True},
            indent=self.VERTICAL + branch,
            is_expandable=False,
            is_expanded=False,
            display_name=label,
            icon=self.icon("change"),
          ))

    result.append(TreeEntry(
      node_id=("cat", "changes"),
      indent=self.BRANCH,
      is_expandable=True,
      is_expanded=("cat", "changes") in self._expanded,
      display_name="Changes",
      icon=self.icon("folder"),
    ))
    if ("cat", "changes") in self._expanded:
      if not unstaged_list:
        result.append(TreeEntry(
          node_id={"type": "empty", "category": "changes"},
          indent=self.VERTICAL + self.LAST_BRANCH,
          is_expandable=False,
          is_expanded=False,
          display_name="(clean)",
          icon=self.icon("file"),
        ))
      else:
        for i, s in enumerate(unstaged_list):
          is_last = i == len(unstaged_list) - 1
          branch = self.LAST_BRANCH if is_last else self.BRANCH
          label = f"{s['status']} {s['path']}"
          result.append(TreeEntry(
            node_id={"type": "change", "path": s["path"], "staged": False, "untracked": False},
            indent=self.VERTICAL + branch,
            is_expandable=False,
            is_expanded=False,
            display_name=label,
            icon=self.icon("change"),
          ))

    result.append(TreeEntry(
      node_id=("cat", "untracked"),
      indent=self.BRANCH,
      is_expandable=True,
      is_expanded=("cat", "untracked") in self._expanded,
      display_name="Untracked",
      icon=self.icon("folder"),
    ))
    if ("cat", "untracked") in self._expanded:
      if not untracked_list:
        result.append(TreeEntry(
          node_id={"type": "empty", "category": "untracked"},
          indent=self.VERTICAL + self.LAST_BRANCH,
          is_expandable=False,
          is_expanded=False,
          display_name="(none)",
          icon=self.icon("file"),
        ))
      else:
        for i, s in enumerate(untracked_list):
          is_last = i == len(untracked_list) - 1
          branch = self.LAST_BRANCH if is_last else self.BRANCH
          label = f"{s['status']} {s['path']}"
          result.append(TreeEntry(
            node_id={"type": "change", "path": s["path"], "staged": False, "untracked": True},
            indent=self.VERTICAL + branch,
            is_expandable=False,
            is_expanded=False,
            display_name=label,
            icon=self.icon("change"),
          ))

    commits = git_viewer.get_commits(wd, 15)
    result.append(TreeEntry(
      node_id=("cat", "commits"),
      indent=self.LAST_BRANCH,
      is_expandable=True,
      is_expanded=("cat", "commits") in self._expanded,
      display_name="Recent Commits",
      icon=self.icon("folder"),
    ))
    if ("cat", "commits") in self._expanded:
      if not commits:
        result.append(TreeEntry(
          node_id={"type": "empty", "category": "commits"},
          indent=self.SPACER + self.LAST_BRANCH,
          is_expandable=False,
          is_expanded=False,
          display_name="(none)",
          icon=self.icon("file"),
        ))
      else:
        for i, c in enumerate(commits):
          is_last = i == len(commits) - 1
          branch = self.LAST_BRANCH if is_last else self.BRANCH
          label = f"{c['hash']} {c['message'][:15]}..."
          result.append(TreeEntry(
            node_id={"type": "commit", "hash": c["full_hash"], "short": c["hash"], "message": c["message"]},
            indent=self.SPACER + branch,
            is_expandable=False,
            is_expanded=False,
            display_name=label,
            icon=self.icon("commit"),
          ))
    return result

  def get_node_buttons(self, node_id, is_expandable) -> list:
    btns = []
    if node_id == ("cat", "staged"):
      staged_list = [s for s in git_viewer.get_status(_get_working_dir()) if s["staged"]]
      all_selected = bool(staged_list) and all(s["path"] in self._selected_for_action for s in staged_list)
      icon = CLEAR_SELECTION if all_selected else SELECT_ALL
      action = "clear_selection" if all_selected else "select_all_staged"
      tooltip = "Clear selection" if all_selected else "Select all staged"
      btns.append(self._make_btn(icon, tooltip, action))
      return btns
    if node_id == ("cat", "changes"):
      unstaged_list = [s for s in git_viewer.get_status(_get_working_dir()) if not s["staged"] and s["status"] != "??"]
      all_selected = bool(unstaged_list) and all(s["path"] in self._selected_for_action for s in unstaged_list)
      icon = CLEAR_SELECTION if all_selected else SELECT_ALL
      action = "clear_selection" if all_selected else "select_all_changes"
      tooltip = "Clear selection" if all_selected else "Select all changes"
      btns.append(self._make_btn(icon, tooltip, action))
      return btns
    if node_id == ("cat", "untracked"):
      untracked_list = [s for s in git_viewer.get_status(_get_working_dir()) if not s["staged"] and s["status"] == "??"]
      all_selected = bool(untracked_list) and all(s["path"] in self._selected_for_action for s in untracked_list)
      icon = CLEAR_SELECTION if all_selected else SELECT_ALL
      action = "clear_selection" if all_selected else "select_all_untracked"
      tooltip = "Clear selection" if all_selected else "Select all untracked"
      btns.append(self._make_btn(icon, tooltip, action))
      return btns
    if isinstance(node_id, dict) and node_id.get("type") == "change":
      path = node_id.get("path", "")
      staged = node_id.get("staged", False)
      untracked = node_id.get("untracked", False)
      label = CHECKED if path in self._selected_for_action else UNCHECKED
      
      if staged:
        btns.append(self._make_btn(GIT_UNSTAGE, "Unstage file", "unstage_file"))
      elif untracked:
        btns.append(self._make_btn(GIT_ADD, "Stage file", "stage_file"))
        
      btns.append(self._make_btn(GIT_DISCARD, "Discard changes", "discard"))
      btns.append(self._make_btn(GIT_IGNORE, "Add to .gitignore", "add_to_gitignore"))
      btns.append(self._make_btn(label, "Toggle for commit/stage/unstage", "toggle_select"))
      return btns
    if isinstance(node_id, dict) and node_id.get("type") == "commit":
      btns.append(self._make_btn(GIT_CHERRY_PICK, "Cherry-pick", "cherry_pick"))
      btns.append(self._make_btn(GIT_BRANCH, "Create branch", "create_branch"))
      return btns
    if isinstance(node_id, dict) and node_id.get("type") == "branch":
      btns.append(self._make_btn(RUN, "Switch to branch", "checkout_branch_btn"))
      btns.append(self._make_btn(DELETE, "Delete branch", "delete_branch"))
      return btns
    return []

  def on_button_action(self, node_id: Any, action: str) -> None:
    wd = _get_working_dir()
    if action == "toggle_select" and isinstance(node_id, dict) and node_id.get("type") == "change":
      path = node_id.get("path", "")
      if path in self._selected_for_action:
        self._selected_for_action.discard(path)
      else:
        self._selected_for_action.add(path)
      self.reload()
      self.post_message(SelectionChanged())
      return
    if action == "stage_file" and isinstance(node_id, dict) and node_id.get("type") == "change":
      path = node_id["path"]
      if git_viewer.stage(wd, path):
        self.app.notify(f"Staged {path}")
        self.reload()
      else:
        self.app.notify(f"Failed to stage {path}", severity="error")
      return
    if action == "unstage_file" and isinstance(node_id, dict) and node_id.get("type") == "change":
      path = node_id["path"]
      if git_viewer.unstage(wd, path):
        self.app.notify(f"Unstaged {path}")
        self.reload()
      else:
        self.app.notify(f"Failed to unstage {path}", severity="error")
      return
    if action == "select_all_staged":
      for s in git_viewer.get_status(wd):
        if s["staged"]:
          self._selected_for_action.add(s["path"])
      self.reload()
      self.post_message(SelectionChanged())
      return
    if action == "select_all_changes":
      for s in git_viewer.get_status(wd):
        if not s["staged"] and s["status"] != "??":
          self._selected_for_action.add(s["path"])
      self.reload()
      self.post_message(SelectionChanged())
      return
    if action == "select_all_untracked":
      for s in git_viewer.get_status(wd):
        if not s["staged"] and s["status"] == "??":
          self._selected_for_action.add(s["path"])
      self.reload()
      self.post_message(SelectionChanged())
      return
    if action == "clear_selection":
      self._selected_for_action.clear()
      self.reload()
      self.post_message(SelectionChanged())
      return
    if action == "discard" and isinstance(node_id, dict) and node_id.get("type") == "change":
      path = node_id["path"]

      def cb(ok: bool | None) -> None:
        if ok and git_viewer.discard(wd, path):
          self._selected_for_action.discard(path)
          self.app.notify("Discarded")
          self.reload()
          self.post_message(SelectionChanged())
        elif ok:
          self.app.notify("Discard failed", severity="error")

      self.app.push_screen(InputModal(f"Discard changes in {path}?", confirm_only=True), cb)
      return
    if action == "add_to_gitignore" and isinstance(node_id, dict) and node_id.get("type") == "change":
      path = node_id["path"]
      if git_viewer.add_to_gitignore(wd, path):
        self.app.notify(f"Added {path} to .gitignore")
        self.reload()
      else:
        self.app.notify("Failed to add to .gitignore", severity="error")
      return
    if action == "cherry_pick" and isinstance(node_id, dict) and node_id.get("type") == "commit":
      commit_hash = node_id["hash"]
      short = node_id.get("short", commit_hash[:7])

      def cb(ok: bool | None) -> None:
        if ok and git_viewer.cherry_pick(wd, commit_hash):
          self.app.notify("Cherry-picked")
          self.reload()
        elif ok:
          self.app.notify("Cherry-pick failed (conflicts?)", severity="error")

      self.app.push_screen(InputModal(f"Cherry-pick {short}?", confirm_only=True), cb)
      return
    if action == "create_branch" and isinstance(node_id, dict) and node_id.get("type") == "commit":
      commit_hash = node_id["hash"]
      short = node_id.get("short", commit_hash[:7])

      def cb(name: str | None) -> None:
        if name and name.strip():
          if git_viewer.create_branch(wd, name.strip(), from_commit=commit_hash):
            self.app.notify(f"Created branch {name.strip()}")
            self.reload()
          else:
            self.app.notify("Create branch failed", severity="error")

      self.app.push_screen(InputModal(f"Branch name from {short}", initial_value=""), cb)
      return
    if action == "checkout_branch_btn" and isinstance(node_id, dict) and node_id.get("type") == "branch":
      name = node_id["name"]
      if node_id.get("is_current"):
        self.app.notify(f"Already on {name}", severity="information")
        return
      success, err_msg = git_viewer.checkout_branch(wd, name)
      if success:
        self.app.notify(f"Switched to {name}")
        self.reload()
      else:
        self.app.notify(f"Checkout failed: {err_msg}", severity="error")
      return
    if action == "delete_branch" and isinstance(node_id, dict) and node_id.get("type") == "branch":
      name = node_id["name"]
      if node_id.get("is_current"):
        self.app.notify(f"Cannot delete current branch {name}", severity="error")
        return
      def cb_delete(ok: bool | None) -> None:
        if ok and git_viewer.delete_branch(wd, name, force=True):
          self.app.notify(f"Deleted branch {name}")
          self.reload()
        elif ok:
          self.app.notify(f"Failed to delete branch {name}", severity="error")

      self.app.push_screen(InputModal(f"Delete branch {name}?", confirm_only=True), cb_delete)
      return
