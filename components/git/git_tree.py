"""Git tree component for the sidebar."""
from typing import Any, Callable

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
    self._expanded.add(("cat", cat_id))

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
          result.append(TreeEntry(
            node_id=node_id_dict,
            indent=child_indent_prefix + branch,
            is_expandable=False,
            is_expanded=False,
            display_name=label,
            icon=self.icon(icon_name),
          ))
    return result

  def get_visible_entries(self) -> list[TreeEntry]:
    result: list[TreeEntry] = []
    wd = _get_working_dir()

    branches = git_viewer.get_branches(wd)
    status_list = git_viewer.get_status(wd)
    commits = git_viewer.get_commits(wd, 15)

    if not branches and not status_list:
      result.append(TreeEntry(
        node_id={"type": "empty"},
        indent="",
        is_expandable=False,
        is_expanded=False,
        display_name="Not a git repository",
        icon=self.icon("git"),
      ))
      return result

    staged_list = [s for s in status_list if s["staged"]]
    unstaged_list = [s for s in status_list if not s["staged"] and s["status"] != "??"]
    untracked_list = [s for s in status_list if not s["staged"] and s["status"] == "??"]

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
      is_last_category=True,
      item_formatter=lambda c: (
        {"type": "commit", "hash": c["full_hash"], "short": c["hash"], "message": c["message"]},
        f"{c['hash']} {c['message'][:15]}..."
      )
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
