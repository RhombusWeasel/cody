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
      result.append({"hash": short_hash, "full_hash": c.hexsha, "message": msg})
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


def checkout_branch(path: str, branch_name: str) -> bool:
  """Checkout branch by name."""
  repo = _get_repo(path)
  if not repo:
    return False
  try:
    repo.heads[branch_name].checkout()
    return True
  except (GitCommandError, IndexError):
    return False
