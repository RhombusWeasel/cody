import os

import git

from utils.cmd_loader import CommandBase
from utils.cfg_man import cfg
from utils.git import is_git_repo, get_file_status
from components.utils.input_modal import preview_then_append_chat_message


def _format_git_status(repo_path: str) -> str:
  if not is_git_repo(repo_path):
    return f"Error: '{repo_path}' is not a git repository."
  try:
    repo = git.Repo(repo_path)
    status = get_file_status(repo)
    staged = status["staged"]
    unstaged = status["unstaged"]
    untracked = status["untracked"]
    lines: list[str] = []
    if not staged and not unstaged and not untracked:
      lines.append("No changes (working tree clean).")
      return "\n".join(lines)
    if staged:
      lines.append("Staged changes:")
      for s in staged:
        lines.append(f"  {s['status']} {s['path']}")
      lines.append("")
    if unstaged:
      lines.append("Unstaged changes:")
      for s in unstaged:
        lines.append(f"  {s['status']} {s['path']}")
      lines.append("")
    if untracked:
      lines.append("Untracked files:")
      for s in untracked:
        lines.append(f"  {s['status']} {s['path']}")
      lines.append("")
    return "\n".join(lines).rstrip()
  except Exception as e:
    return f"Error getting status: {e}"


class GstatusCommand(CommandBase):
  description = "Git status for the session directory (preview, then add to chat)"

  async def execute(self, app, args: list[str]):
    try:
      wd = cfg.get("session.working_directory", os.getcwd())
      body = _format_git_status(wd)
      await preview_then_append_chat_message(app, "Git status", body)
    except Exception as e:
      print(f"gstatus command failed: {e}")
