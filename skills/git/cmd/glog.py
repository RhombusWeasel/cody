import os

import git

from utils.cmd_loader import CommandBase
from utils.cfg_man import cfg
from utils.git import is_git_repo, get_recent_commits
from components.utils.input_modal import preview_then_append_chat_message


def _format_log(repo_path: str, count: int) -> str:
  if not is_git_repo(repo_path):
    return f"Error: '{repo_path}' is not a git repository."
  try:
    repo = git.Repo(repo_path)
    commits = get_recent_commits(repo, count)
    if not commits:
      return "No commits found."
    lines = [f"Recent commits (up to {count}):"]
    for c in commits:
      lines.append(f"{c['hash']} - {c['time']} - {c['message']}")
    return "\n".join(lines)
  except Exception as e:
    return f"Error getting commits: {e}"


class GlogCommand(CommandBase):
  description = "Recent git log for session directory (optional count); preview then add to chat"

  async def execute(self, app, args: list[str]):
    try:
      wd = cfg.get("session.working_directory", os.getcwd())
      count = 10
      if args:
        try:
          count = max(1, min(500, int(args[0])))
        except ValueError:
          count = 10
      body = _format_log(wd, count)
      await preview_then_append_chat_message(app, "Git log", body)
    except Exception as e:
      print(f"glog command failed: {e}")
