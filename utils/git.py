"""Git utilities for checkpoint and revert operations."""
import os
import git
from git.exc import InvalidGitRepositoryError


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
  """Snapshot current state without staging or committing. Returns a ref for later revert."""
  try:
    repo = git.Repo(path)
    stash_sha = repo.git.stash("create").strip()
    if stash_sha:
      return stash_sha
    if repo.head.is_valid():
      return repo.head.commit.hexsha
    return None
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


def _parse_diff_name_status(output: str) -> list[dict]:
  """Parse `git diff --name-status` lines into [{"path", "status"}, ...]."""
  rows: list[dict] = []
  for line in output.splitlines():
    line = line.strip()
    if not line:
      continue
    parts = line.split("\t")
    if len(parts) < 2:
      continue
    tag = parts[0].strip()
    if not tag:
      continue
    letter = tag[0]
    if letter in ("R", "C") and len(parts) >= 3:
      path = parts[2]
    else:
      path = parts[1]
    rows.append({"path": path, "status": letter})
  return rows


def get_file_status(repo: git.Repo) -> dict[str, list[dict]]:
  """Get staged, unstaged, and untracked files from a repo.

  Uses porcelain `git diff --name-status` so staged deletions show as D (GitPython
  index.diff('HEAD') mislabels them as A due to reverse diff semantics).
  """
  staged: list[dict] = []
  unstaged: list[dict] = []
  untracked: list[dict] = []
  try:
    cached_raw = repo.git.diff("--cached", "--name-status") or ""
    staged = _parse_diff_name_status(cached_raw)
    unstaged_raw = repo.git.diff("--name-status") or ""
    unstaged = _parse_diff_name_status(unstaged_raw)
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


def get_stashes(repo: git.Repo) -> list[dict]:
  """Get stash list as [{index, message}]."""
  stashes = []
  try:
    raw = repo.git.stash("list")
    for line in raw.splitlines():
      if not line.strip():
        continue
      parts = line.split(":", 2)
      index = int(parts[0].replace("stash@{", "").replace("}", "").strip()) if parts else len(stashes)
      message = parts[2].strip() if len(parts) > 2 else line.strip()
      stashes.append({"index": index, "message": message})
  except Exception:
    pass
  return stashes


def create_stash(repo: git.Repo, message: str = "WIP") -> bool:
  """Stash current working directory changes."""
  try:
    repo.git.stash("push", "-u", "-m", message)
    return True
  except Exception:
    return False


def pop_stash(repo: git.Repo, index: int = 0) -> bool:
  """Pop a stash by index."""
  try:
    repo.git.stash("pop", f"stash@{{{index}}}")
    return True
  except Exception:
    return False


def drop_stash(repo: git.Repo, index: int = 0) -> bool:
  """Drop a stash by index without applying it."""
  try:
    repo.git.stash("drop", f"stash@{{{index}}}")
    return True
  except Exception:
    return False


def revert_commit(repo: git.Repo, commit_hash: str) -> bool:
  """Create a revert commit for the given commit hash."""
  try:
    repo.git.revert(commit_hash, "--no-edit")
    return True
  except Exception:
    return False


def merge_branch(repo: git.Repo, branch_name: str) -> bool:
  """Merge the given branch into the current branch."""
  try:
    repo.git.merge(branch_name)
    return True
  except Exception:
    return False


def rename_branch(repo: git.Repo, old_name: str, new_name: str) -> bool:
  """Rename a local branch."""
  try:
    repo.heads[old_name].rename(new_name)
    return True
  except Exception:
    return False
