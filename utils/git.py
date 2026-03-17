"""Git utilities for checkpoint and revert operations."""
import subprocess
import os


def is_git_repo(path: str) -> bool:
  """Check if path is a git repository."""
  git_dir = os.path.join(path, ".git")
  return os.path.isdir(git_dir)


def ensure_git_repo(path: str) -> bool:
  """Initialize git repo if not already one. Returns True if repo exists."""
  if is_git_repo(path):
    return True
  try:
    subprocess.run(
      ["git", "init"],
      cwd=path,
      check=True,
      capture_output=True,
    )
    return True
  except (subprocess.CalledProcessError, FileNotFoundError):
    return False


def create_checkpoint(path: str, message: str) -> str | None:
  """Stage all, commit, return commit hash. Uses --allow-empty if nothing to commit."""
  if not is_git_repo(path):
    return None
  try:
    subprocess.run(
      ["git", "add", "."],
      cwd=path,
      check=True,
      capture_output=True,
    )
    result = subprocess.run(
      ["git", "commit", "-m", message],
      cwd=path,
      capture_output=True,
      text=True,
    )
    if result.returncode != 0:
      subprocess.run(
        ["git", "commit", "--allow-empty", "-m", message],
        cwd=path,
        check=True,
        capture_output=True,
      )
    rev_result = subprocess.run(
      ["git", "rev-parse", "HEAD"],
      cwd=path,
      capture_output=True,
      text=True,
    )
    if rev_result.returncode == 0:
      return rev_result.stdout.strip()
    return None
  except (subprocess.CalledProcessError, FileNotFoundError):
    return None


def revert_to_checkpoint(path: str, commit_hash: str) -> bool:
  """Restore working tree to commit. Keeps HEAD, restores files."""
  if not is_git_repo(path):
    return False
  try:
    subprocess.run(
      ["git", "restore", "--source", commit_hash, "."],
      cwd=path,
      check=True,
      capture_output=True,
    )
    return True
  except (subprocess.CalledProcessError, FileNotFoundError):
    return False
