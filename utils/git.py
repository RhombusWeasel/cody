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
