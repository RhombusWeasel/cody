"""Git tree component for the sidebar."""
from typing import Any, Callable

import git
from textual.message import Message

from components.tree import GenericTree
from components.git.git_tree_actions import handle_git_action
from utils.cfg_man import cfg
from utils.tree_model import TreeEntry
from utils.git import get_file_status, get_branches_info, get_recent_commits, get_stashes
from utils.icons import (
  GIT_ICON_SET, CHECKED, UNCHECKED, SELECT_ALL, CLEAR_SELECTION,
  GIT_DISCARD, GIT_IGNORE, GIT_CHERRY_PICK, GIT_BRANCH, RUN, DELETE,
  GIT_ADD, GIT_UNSTAGE, GIT_MERGE, GIT_REVERT, EDIT,
)


class SelectionChanged(Message, bubble=True):
  """Posted when the selected-for-action set changes."""


def _get_working_dir() -> str:
  return cfg.get("session.working_directory", ".")


class GitTree(GenericTree):
  """Flat git tree - branches, changes, commits, stashes."""

  def __init__(self, selected_for_action: set[str] | None = None, **kwargs):
    self._selected_for_action = selected_for_action or set()
    self.staged_paths: set[str] = set()
    self.unstaged_paths: set[str] = set()
    self.untracked_paths: set[str] = set()
    super().__init__(icon_set=GIT_ICON_SET, **kwargs)
    self._expanded.update([
      ("cat", "branches"),
      ("cat", "staged"),
      ("cat", "changes"),
      ("cat", "untracked"),
      ("cat", "commits"),
      ("cat", "stashes"),
    ])

  def _build_category(
    self,
    cat_id: str,
    display_name: str,
    items: list[Any],
    empty_text: str,
    icon_name: str,
    is_last_category: bool,
    item_formatter: Callable[[Any], tuple[dict, str]]
  ) -> list[TreeEntry]:
    result: list[TreeEntry] = []

    cat_indent = self.LAST_BRANCH if is_last_category else self.BRANCH
    child_indent_prefix = self.SPACER if is_last_category else self.VERTICAL

    result.append(TreeEntry(
      node_id=("cat", cat_id),
      indent=cat_indent,
      is_expandable=True,
      is_expanded=("cat", cat_id) in self._expanded,
      display_name=display_name,
      icon=self.icon("folder"),
    ))

    if ("cat", cat_id) in self._expanded:
      if not items:
        result.append(TreeEntry(
          node_id={"type": "empty", "category": cat_id},
          indent=child_indent_prefix + self.LAST_BRANCH,
          is_expandable=False,
          is_expanded=False,
          display_name=empty_text,
          icon=self.icon("file"),
        ))
      else:
        for i, item in enumerate(items):
          is_last = i == len(items) - 1
          branch = self.LAST_BRANCH if is_last else self.BRANCH
          node_id_dict, label = item_formatter(item)
          label_max = 25
          if node_id_dict["type"] == "commit":
            label_text = label[:label_max] + '...' if len(label) > label_max else label
          else:
            label_text = '...' + label[-label_max:] if len(label) > label_max else label
          result.append(TreeEntry(
            node_id=node_id_dict,
            indent=child_indent_prefix + branch,
            is_expandable=False,
            is_expanded=False,
            display_name=label_text,
            icon=self.icon(icon_name),
          ))
    return result

  def get_visible_entries(self) -> list[TreeEntry]:
    result: list[TreeEntry] = []
    wd = _get_working_dir()

    try:
      repo = git.Repo(wd)
    except git.exc.InvalidGitRepositoryError:
      result.append(TreeEntry(
        node_id={"type": "empty"},
        indent="",
        is_expandable=False,
        is_expanded=False,
        display_name="Not a git repository",
        icon=self.icon("git"),
      ))
      return result

    branches = get_branches_info(repo)
    status = get_file_status(repo)
    staged_list = [{"path": s["path"], "status": s["status"], "staged": True} for s in status["staged"]]
    unstaged_list = [{"path": s["path"], "status": s["status"], "staged": False} for s in status["unstaged"]]
    untracked_list = [{"path": s["path"], "status": s["status"], "staged": False} for s in status["untracked"]]
    commits = get_recent_commits(repo, 15)
    stashes = get_stashes(repo)

    self.staged_paths = {s["path"] for s in staged_list}
    self.unstaged_paths = {s["path"] for s in unstaged_list}
    self.untracked_paths = {s["path"] for s in untracked_list}

    result.extend(self._build_category(
      cat_id="branches",
      display_name="Branches",
      items=branches,
      empty_text="(no commits yet)",
      icon_name="branch",
      is_last_category=False,
      item_formatter=lambda b: (
        {"type": "branch", "name": b["name"], "is_current": b["is_current"]},
        f"{b['name']} *" if b["is_current"] else b["name"]
      )
    ))

    result.extend(self._build_category(
      cat_id="staged",
      display_name="Staged",
      items=staged_list,
      empty_text="(none)",
      icon_name="change",
      is_last_category=False,
      item_formatter=lambda s: (
        {"type": "change", "path": s["path"], "staged": True},
        f"{s['status']} {s['path']}"
      )
    ))

    result.extend(self._build_category(
      cat_id="changes",
      display_name="Changes",
      items=unstaged_list,
      empty_text="(clean)",
      icon_name="change",
      is_last_category=False,
      item_formatter=lambda s: (
        {"type": "change", "path": s["path"], "staged": False, "untracked": False},
        f"{s['status']} {s['path']}"
      )
    ))

    result.extend(self._build_category(
      cat_id="untracked",
      display_name="Untracked",
      items=untracked_list,
      empty_text="(none)",
      icon_name="change",
      is_last_category=False,
      item_formatter=lambda s: (
        {"type": "change", "path": s["path"], "staged": False, "untracked": True},
        f"{s['status']} {s['path']}"
      )
    ))

    result.extend(self._build_category(
      cat_id="commits",
      display_name="Recent Commits",
      items=commits,
      empty_text="(none)",
      icon_name="commit",
      is_last_category=False,
      item_formatter=lambda c: (
        {"type": "commit", "hash": c["full_hash"], "short": c["hash"], "message": c["message"], "time": c["time"]},
        f"{c['hash']} {c['time']}"
      )
    ))

    result.extend(self._build_category(
      cat_id="stashes",
      display_name="Stashes",
      items=stashes,
      empty_text="(none)",
      icon_name="stash",
      is_last_category=True,
      item_formatter=lambda s: (
        {"type": "stash", "index": s["index"], "message": s["message"]},
        s["message"]
      )
    ))

    return result

  def get_node_buttons(self, node_id, is_expandable) -> list:
    btns = []

    if node_id == ("cat", "staged"):
      all_selected = bool(self.staged_paths) and self.staged_paths.issubset(self._selected_for_action)
      icon = CLEAR_SELECTION if all_selected else SELECT_ALL
      action = "clear_selection" if all_selected else "select_all_staged"
      tooltip = "Clear selection" if all_selected else "Select all staged"
      btns.append(self._make_btn(icon, tooltip, action))
      return btns

    if node_id == ("cat", "changes"):
      all_selected = bool(self.unstaged_paths) and self.unstaged_paths.issubset(self._selected_for_action)
      icon = CLEAR_SELECTION if all_selected else SELECT_ALL
      action = "clear_selection" if all_selected else "select_all_changes"
      tooltip = "Clear selection" if all_selected else "Select all changes"
      btns.append(self._make_btn(icon, tooltip, action))
      return btns

    if node_id == ("cat", "untracked"):
      all_selected = bool(self.untracked_paths) and self.untracked_paths.issubset(self._selected_for_action)
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
      else:
        btns.append(self._make_btn(GIT_ADD, "Stage file", "stage_file"))

      btns.append(self._make_btn(GIT_DISCARD, "Discard changes", "discard"))
      btns.append(self._make_btn(GIT_IGNORE, "Add to .gitignore", "add_to_gitignore"))
      btns.append(self._make_btn(label, "Toggle for commit/stage/unstage", "toggle_select"))
      return btns

    if isinstance(node_id, dict) and node_id.get("type") == "commit":
      btns.append(self._make_btn(GIT_CHERRY_PICK, "Cherry-pick", "cherry_pick"))
      btns.append(self._make_btn(GIT_REVERT, "Revert commit", "revert_commit"))
      btns.append(self._make_btn(GIT_BRANCH, "Create branch", "create_branch"))
      return btns

    if isinstance(node_id, dict) and node_id.get("type") == "branch":
      btns.append(self._make_btn(RUN, "Switch to branch", "checkout_branch_btn"))
      btns.append(self._make_btn(GIT_MERGE, "Merge into current", "merge_branch"))
      btns.append(self._make_btn(EDIT, "Rename branch", "rename_branch"))
      btns.append(self._make_btn(DELETE, "Delete branch", "delete_branch"))
      return btns

    if isinstance(node_id, dict) and node_id.get("type") == "stash":
      btns.append(self._make_btn(RUN, "Pop stash", "pop_stash"))
      btns.append(self._make_btn(DELETE, "Drop stash", "drop_stash"))
      return btns

    return []

  def on_button_action(self, node_id: Any, action: str) -> None:
    wd = _get_working_dir()
    try:
      repo = git.Repo(wd)
    except git.exc.InvalidGitRepositoryError:
      return

    handle_git_action(
      app=self.app,
      repo=repo,
      wd=wd,
      node_id=node_id,
      action=action,
      selected=self._selected_for_action,
      reload_cb=self.reload,
      selection_changed_cb=lambda: self.post_message(SelectionChanged()),
    )
