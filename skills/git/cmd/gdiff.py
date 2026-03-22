import os

import git

from utils.cmd_loader import CommandBase
from utils.cfg_man import cfg
from utils.git import is_git_repo
from components.utils.input_modal import preview_then_append_chat_message


def _git_diff_text(repo_path: str, staged: bool, file_path: str | None) -> str:
  if not is_git_repo(repo_path):
    return f"Error: '{repo_path}' is not a git repository."
  try:
    repo = git.Repo(repo_path)
    if staged:
      diff_output = repo.git.diff("--cached", "--", file_path) if file_path else repo.git.diff("--cached")
    else:
      diff_output = repo.git.diff("--", file_path) if file_path else repo.git.diff()
    return diff_output or "(no changes)"
  except Exception as e:
    return f"Error getting diff: {e}"


class GdiffCommand(CommandBase):
  description = "Git diff (optional --staged, optional file path); preview then add to chat"

  async def execute(self, app, args: list[str]):
    try:
      wd = cfg.get("session.working_directory", os.getcwd())
      tokens = list(args)
      staged = "--staged" in tokens
      tokens = [t for t in tokens if t != "--staged"]
      file_path = " ".join(tokens).strip() or None
      body = _git_diff_text(wd, staged, file_path)
      title = "Git diff (staged)" if staged else "Git diff"
      await preview_then_append_chat_message(app, title, body)
    except Exception as e:
      print(f"gdiff command failed: {e}")
