"""Git viewer utilities using GitPython. Data-fetching for sidebar git tab."""
from __future__ import annotations

from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError

from utils.git import is_git_repo


def _get_repo(path: str) -> Repo | None:
  if not is_git_repo(path):
    return None
  try:
    return Repo(path)
  except InvalidGitRepositoryError:
    return None


def get_status(path: str) -> list[dict]:
  """Return list of {path, status, staged} for changed files. status: M, A, D, ??, etc."""
  repo = _get_repo(path)
  if not repo:
    return []

  result = []
  try:
    staged_diffs = list(repo.index.diff("HEAD", create_patch=False)) if repo.head.is_valid() else []
    unstaged_diffs = list(repo.index.diff(None, create_patch=False))

    staged_paths = {d.a_path for d in staged_diffs}
    for d in staged_diffs:
      change_type = d.change_type
      letter = "A" if change_type == "A" else "D" if change_type == "D" else "M"
      result.append({"path": d.a_path, "status": letter, "staged": True})

    for d in unstaged_diffs:
      if d.a_path not in staged_paths:
        change_type = d.change_type
        letter = "A" if change_type == "A" else "D" if change_type == "D" else "M"
        result.append({"path": d.a_path, "status": letter, "staged": False})

    for p in repo.untracked_files:
      result.append({"path": p, "status": "??", "staged": False})
  except GitCommandError:
    pass
  return result


def get_branches(path: str) -> list[dict]:
  """Return list of {name, is_current} for local branches."""
  repo = _get_repo(path)
  if not repo:
    return []

  result = []
  try:
    current = repo.head.ref.name if repo.head.is_valid() and not repo.head.is_detached else None
    for ref in repo.heads:
      result.append({"name": ref.name, "is_current": ref.name == current})
  except GitCommandError:
    pass
  return result


def get_commits(path: str, n: int = 20) -> list[dict]:
  """Return list of {hash, message} for recent commits."""
  repo = _get_repo(path)
  if not repo or not repo.head.is_valid():
    return []

  result = []
  try:
    for c in repo.iter_commits(max_count=n):
      short_hash = c.hexsha[:7] if len(c.hexsha) >= 7 else c.hexsha
      msg = (c.message or "").split("\n")[0].strip()
      time_str = c.committed_datetime.strftime("%Y-%m-%d %H:%M")
      result.append({"hash": short_hash, "full_hash": c.hexsha, "message": msg, "time": time_str})
  except GitCommandError:
    pass
  return result


def get_diff(repo_path: str, file_path: str | None = None, staged: bool = False) -> str:
  """Return diff string for file or all. staged=True for --cached."""
  repo = _get_repo(repo_path)
  if not repo:
    return ""

  try:
    if staged:
      out = repo.git.diff("--cached", "--", file_path) if file_path else repo.git.diff("--cached")
    else:
      out = repo.git.diff("--", file_path) if file_path else repo.git.diff()
    return out or "(no changes)"
  except GitCommandError as e:
    return str(e)


def get_commit_diff(path: str, commit_hash: str, file_path: str | None = None) -> str:
  """Return diff for a specific commit."""
  repo = _get_repo(path)
  if not repo:
    return ""

  try:
    if file_path:
      out = repo.git.show(commit_hash, "--", file_path)
    else:
      out = repo.git.show(commit_hash)
    return out or "(empty)"
  except GitCommandError as e:
    return str(e)


def stage(path: str, file_path: str | None = None) -> bool:
  """Stage file or all. file_path=None stages all."""
  repo = _get_repo(path)
  if not repo:
    return False
  try:
    if file_path:
      repo.index.add([file_path])
    else:
      repo.git.add(".")
    return True
  except GitCommandError:
    return False


def unstage(path: str, file_path: str | None = None) -> bool:
  """Unstage file or all."""
  repo = _get_repo(path)
  if not repo:
    return False
  try:
    if file_path:
      repo.git.reset("HEAD", file_path)
    else:
      repo.git.reset("HEAD")
    return True
  except GitCommandError:
    return False


def commit(path: str, message: str) -> bool:
  """Commit staged changes."""
  repo = _get_repo(path)
  if not repo:
    return False
  try:
    repo.index.commit(message)
    return True
  except GitCommandError:
    return False


def checkout_branch(path: str, branch_name: str) -> tuple[bool, str]:
  """Checkout branch by name. Returns (success, error_message)."""
  repo = _get_repo(path)
  if not repo:
    return False, "Not a git repository"
  try:
    repo.heads[branch_name].checkout()
    return True, ""
  except GitCommandError as e:
    # Extract just the stderr part of the GitCommandError for a cleaner message
    err_msg = e.stderr.strip() if e.stderr else str(e)
    return False, err_msg
  except IndexError:
    return False, f"Branch '{branch_name}' not found"


def discard(path: str, file_path: str) -> bool:
  """Discard changes in working tree for file. Unstages if staged, restores from index/HEAD."""
  repo = _get_repo(path)
  if not repo:
    return False
  try:
    repo.git.checkout("--", file_path)
    repo.git.reset("HEAD", file_path)
    return True
  except GitCommandError:
    return False


def add_to_gitignore(repo_path: str, entry: str) -> bool:
  """Append path to .gitignore."""
  from pathlib import Path
  gitignore = Path(repo_path) / ".gitignore"
  try:
    with open(gitignore, "a") as f:
      f.write(f"\n{entry}\n")
    return True
  except OSError:
    return False


def cherry_pick(path: str, commit_hash: str) -> bool:
  """Cherry-pick commit onto current branch."""
  repo = _get_repo(path)
  if not repo:
    return False
  try:
    repo.git.cherry_pick(commit_hash)
    return True
  except GitCommandError:
    return False


def create_branch(path: str, branch_name: str, from_commit: str | None = None) -> bool:
  """Create branch, optionally from specific commit. Does not checkout."""
  repo = _get_repo(path)
  if not repo:
    return False
  try:
    if from_commit:
      repo.git.branch(branch_name, from_commit)
    else:
      repo.git.branch(branch_name)
    return True
  except GitCommandError:
    return False


def delete_branch(path: str, branch_name: str, force: bool = False) -> bool:
  """Delete a local branch."""
  repo = _get_repo(path)
  if not repo:
    return False
  try:
    if force:
      repo.git.branch("-D", branch_name)
    else:
      repo.git.branch("-d", branch_name)
    return True
  except GitCommandError:
    return False
