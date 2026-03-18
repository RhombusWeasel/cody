"""Git utilities for checkpoint and revert operations."""
import os
import git
from git.exc import InvalidGitRepositoryError, GitCommandError


def is_git_repo(path: str) -> bool:
  """Check if path is a git repository."""
  try:
    git.Repo(path)
    return True
  except InvalidGitRepositoryError:
    return False


def ensure_git_repo(path: str) -> bool:
  """Initialize git repo if not already one. Returns True if repo exists."""
  if is_git_repo(path):
    return True
  try:
    git.Repo.init(path)
    return True
  except Exception:
    return False


def create_checkpoint(path: str, message: str) -> str | None:
  """Stage all, commit, return commit hash. Uses --allow-empty if nothing to commit."""
  try:
    repo = git.Repo(path)
    repo.git.add(".")
    try:
      repo.git.commit("-m", message)
    except GitCommandError:
      repo.git.commit("--allow-empty", "-m", message)
    return repo.head.commit.hexsha
  except Exception:
    return None


def revert_to_checkpoint(path: str, commit_hash: str) -> bool:
  """Restore working tree to commit. Keeps HEAD, restores files."""
  try:
    repo = git.Repo(path)
    repo.git.restore("--source", commit_hash, ".")
    return True
  except Exception:
    return False


def get_file_status(repo: git.Repo) -> dict[str, list[dict]]:
  """Get staged, unstaged, and untracked files from a repo."""
  staged = []
  unstaged = []
  untracked = []
  
  try:
    staged_diffs = list(repo.index.diff("HEAD", create_patch=False)) if repo.head.is_valid() else []
    unstaged_diffs = list(repo.index.diff(None, create_patch=False))

    staged_paths = {d.a_path for d in staged_diffs}
    for d in staged_diffs:
      letter = "A" if d.change_type == "A" else "D" if d.change_type == "D" else "M"
      staged.append({"path": d.a_path, "status": letter})

    for d in unstaged_diffs:
      if d.a_path not in staged_paths:
        letter = "A" if d.change_type == "A" else "D" if d.change_type == "D" else "M"
        unstaged.append({"path": d.a_path, "status": letter})

    for p in repo.untracked_files:
      untracked.append({"path": p, "status": "??"})
  except Exception:
    pass
    
  return {"staged": staged, "unstaged": unstaged, "untracked": untracked}


def get_branches_info(repo: git.Repo) -> list[dict]:
  """Get local branches and identify the current one."""
  branches = []
  try:
    current = repo.head.ref.name if repo.head.is_valid() and not repo.head.is_detached else None
    for ref in repo.heads:
      branches.append({"name": ref.name, "is_current": ref.name == current})
  except Exception:
    pass
  return branches


def get_recent_commits(repo: git.Repo, max_count: int = 15) -> list[dict]:
  """Get recent commits."""
  commits = []
  if repo.head.is_valid():
    try:
      for c in repo.iter_commits(max_count=max_count):
        short_hash = c.hexsha[:7] if len(c.hexsha) >= 7 else c.hexsha
        msg = (c.message or "").split("\n")[0].strip()
        time_str = c.committed_datetime.strftime("%Y-%m-%d %H:%M")
        commits.append({"hash": short_hash, "full_hash": c.hexsha, "message": msg, "time": time_str})
    except Exception:
      pass
  return commits


def stage_all(repo: git.Repo) -> None:
  """Stage all untracked files and unstaged changes."""
  if repo.untracked_files:
    repo.index.add(repo.untracked_files)
  diffs = [item.a_path for item in repo.index.diff(None)]
  if diffs:
    repo.index.add(diffs)
