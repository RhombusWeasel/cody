"""Action handler for GitTree button presses."""
from pathlib import Path
from typing import Any, Callable

import git

from components.utils.input_modal import InputModal
from utils.git import (
  pop_stash, drop_stash, revert_commit, merge_branch, rename_branch
)


def handle_git_action(
  app,
  repo: git.Repo,
  wd: str,
  node_id: Any,
  action: str,
  selected: set[str],
  reload_cb: Callable,
  selection_changed_cb: Callable,
) -> None:
  """Dispatch a git tree button action."""

  # --- Selection ---
  if action == "toggle_select" and isinstance(node_id, dict) and node_id.get("type") == "change":
    path = node_id.get("path", "")
    if path in selected:
      selected.discard(path)
    else:
      selected.add(path)
    reload_cb()
    selection_changed_cb()
    return

  if action == "select_all_staged":
    selected.update(_staged_paths(repo))
    reload_cb()
    selection_changed_cb()
    return

  if action == "select_all_changes":
    selected.update(_unstaged_paths(repo))
    reload_cb()
    selection_changed_cb()
    return

  if action == "select_all_untracked":
    selected.update(_untracked_paths(repo))
    reload_cb()
    selection_changed_cb()
    return

  if action == "clear_selection":
    selected.clear()
    reload_cb()
    selection_changed_cb()
    return

  # --- File actions ---
  if action == "stage_file" and isinstance(node_id, dict) and node_id.get("type") == "change":
    path = node_id["path"]
    try:
      repo.index.add([path])
      app.notify(f"Staged {path}")
      reload_cb()
    except Exception:
      app.notify(f"Failed to stage {path}", severity="error")
    return

  if action == "unstage_file" and isinstance(node_id, dict) and node_id.get("type") == "change":
    path = node_id["path"]
    try:
      repo.head.reset(paths=[path])
      app.notify(f"Unstaged {path}")
      reload_cb()
    except Exception:
      app.notify(f"Failed to unstage {path}", severity="error")
    return

  if action == "discard" and isinstance(node_id, dict) and node_id.get("type") == "change":
    path = node_id["path"]

    def cb_discard(ok: bool | None) -> None:
      if ok:
        try:
          repo.head.reset(paths=[path])
          repo.index.checkout(paths=[path], force=True)
          selected.discard(path)
          app.notify("Discarded")
          reload_cb()
          selection_changed_cb()
        except Exception:
          app.notify("Discard failed", severity="error")

    app.push_screen(InputModal(f"Discard changes in {path}?", confirm_only=True), cb_discard)
    return

  if action == "add_to_gitignore" and isinstance(node_id, dict) and node_id.get("type") == "change":
    path = node_id["path"]
    try:
      with open(Path(wd) / ".gitignore", "a") as f:
        f.write(f"\n{path}\n")
      app.notify(f"Added {path} to .gitignore")
      reload_cb()
    except OSError:
      app.notify("Failed to add to .gitignore", severity="error")
    return

  # --- Commit actions ---
  if action == "cherry_pick" and isinstance(node_id, dict) and node_id.get("type") == "commit":
    commit_hash = node_id["hash"]
    short = node_id.get("short", commit_hash[:7])

    def cb_cherry(ok: bool | None) -> None:
      if ok:
        try:
          repo.git.cherry_pick(commit_hash)
          app.notify("Cherry-picked")
          reload_cb()
        except git.exc.GitCommandError:
          app.notify("Cherry-pick failed (conflicts?)", severity="error")

    app.push_screen(InputModal(f"Cherry-pick {short}?", confirm_only=True), cb_cherry)
    return

  if action == "create_branch" and isinstance(node_id, dict) and node_id.get("type") == "commit":
    commit_hash = node_id["hash"]
    short = node_id.get("short", commit_hash[:7])

    def cb_create(name: str | None) -> None:
      if name and name.strip():
        try:
          repo.create_head(name.strip(), commit=commit_hash)
          app.notify(f"Created branch {name.strip()}")
          reload_cb()
        except Exception:
          app.notify("Create branch failed", severity="error")

    app.push_screen(InputModal(f"Branch name from {short}", initial_value=""), cb_create)
    return

  if action == "revert_commit" and isinstance(node_id, dict) and node_id.get("type") == "commit":
    commit_hash = node_id["hash"]
    short = node_id.get("short", commit_hash[:7])

    def cb_revert(ok: bool | None) -> None:
      if ok:
        if revert_commit(repo, commit_hash):
          app.notify(f"Reverted {short}")
          reload_cb()
        else:
          app.notify("Revert failed (conflicts?)", severity="error")

    app.push_screen(InputModal(f"Revert commit {short}?", confirm_only=True), cb_revert)
    return

  # --- Branch actions ---
  if action == "checkout_branch_btn" and isinstance(node_id, dict) and node_id.get("type") == "branch":
    name = node_id["name"]
    if node_id.get("is_current"):
      app.notify(f"Already on {name}", severity="information")
      return
    try:
      repo.heads[name].checkout()
      app.notify(f"Switched to {name}")
      reload_cb()
    except Exception as e:
      err_msg = getattr(e, "stderr", str(e)).strip()
      app.notify(f"Checkout failed: {err_msg}", severity="error")
    return

  if action == "delete_branch" and isinstance(node_id, dict) and node_id.get("type") == "branch":
    name = node_id["name"]
    if node_id.get("is_current"):
      app.notify(f"Cannot delete current branch {name}", severity="error")
      return

    def cb_delete(ok: bool | None) -> None:
      if ok:
        try:
          repo.delete_head(name, force=True)
          app.notify(f"Deleted branch {name}")
          reload_cb()
        except Exception:
          app.notify(f"Failed to delete branch {name}", severity="error")

    app.push_screen(InputModal(f"Delete branch {name}?", confirm_only=True), cb_delete)
    return

  if action == "merge_branch" and isinstance(node_id, dict) and node_id.get("type") == "branch":
    name = node_id["name"]
    if node_id.get("is_current"):
      app.notify(f"Cannot merge branch into itself", severity="warning")
      return

    def cb_merge(ok: bool | None) -> None:
      if ok:
        if merge_branch(repo, name):
          app.notify(f"Merged {name}")
          reload_cb()
        else:
          app.notify(f"Merge failed (conflicts?)", severity="error")

    app.push_screen(InputModal(f"Merge {name} into current branch?", confirm_only=True), cb_merge)
    return

  if action == "rename_branch" and isinstance(node_id, dict) and node_id.get("type") == "branch":
    old_name = node_id["name"]

    def cb_rename(new_name: str | None) -> None:
      if new_name and new_name.strip():
        if rename_branch(repo, old_name, new_name.strip()):
          app.notify(f"Renamed to {new_name.strip()}")
          reload_cb()
        else:
          app.notify("Rename failed", severity="error")

    app.push_screen(InputModal(f"Rename branch {old_name}", initial_value=old_name), cb_rename)
    return

  # --- Stash actions ---
  if action == "pop_stash" and isinstance(node_id, dict) and node_id.get("type") == "stash":
    index = node_id.get("index", 0)
    if pop_stash(repo, index):
      app.notify("Stash applied")
      reload_cb()
    else:
      app.notify("Pop stash failed (conflicts?)", severity="error")
    return

  if action == "drop_stash" and isinstance(node_id, dict) and node_id.get("type") == "stash":
    index = node_id.get("index", 0)
    message = node_id.get("message", f"stash@{{{index}}}")

    def cb_drop(ok: bool | None) -> None:
      if ok:
        if drop_stash(repo, index):
          app.notify("Stash dropped")
          reload_cb()
        else:
          app.notify("Drop stash failed", severity="error")

    app.push_screen(InputModal(f"Drop stash: {message}?", confirm_only=True), cb_drop)
    return


def _staged_paths(repo: git.Repo) -> set[str]:
  try:
    return {d.a_path for d in repo.index.diff("HEAD")} if repo.head.is_valid() else set()
  except Exception:
    return set()


def _unstaged_paths(repo: git.Repo) -> set[str]:
  try:
    staged = _staged_paths(repo)
    return {d.a_path for d in repo.index.diff(None) if d.a_path not in staged}
  except Exception:
    return set()


def _untracked_paths(repo: git.Repo) -> set[str]:
  try:
    return set(repo.untracked_files)
  except Exception:
    return set()
