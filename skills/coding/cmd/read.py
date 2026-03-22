import os

from utils.cmd_loader import CommandBase
from utils.cfg_man import cfg
from components.utils.input_modal import preview_then_append_chat_message


class ReadCommand(CommandBase):
  description = "Read a file with line numbers (preview, then add to chat)"

  async def execute(self, app, args: list[str]):
    try:
      if not args:
        await preview_then_append_chat_message(app, "read", "Usage: /read <path>")
        return
      wd = cfg.get("session.working_directory", os.getcwd())
      rel = args[0]
      path = rel if os.path.isabs(rel) else os.path.normpath(os.path.join(wd, rel))
      if not os.path.isfile(path):
        await preview_then_append_chat_message(app, "read", f"Error: not a file: {path}")
        return
      try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
          content = f.read()
      except OSError as e:
        await preview_then_append_chat_message(app, "read", f"Error: {e}")
        return
      lines = content.split("\n")
      body = "\n".join(f"{i + 1:6}|{line}" for i, line in enumerate(lines))
      display = rel if not os.path.isabs(rel) else path
      await preview_then_append_chat_message(app, f"File: {display}", body)
    except Exception as e:
      print(f"read command failed: {e}")
