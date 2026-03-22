import importlib.util
import os

from utils.cmd_loader import CommandBase
from components.utils.input_modal import preview_then_append_chat_message

_cmd_dir = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("_todo_cmd_common", os.path.join(_cmd_dir, "__todo_common.py"))
_uc = importlib.util.module_from_spec(_spec)
assert _spec.loader
_spec.loader.exec_module(_uc)


class DoneCommand(CommandBase):
  description = "Mark a todo completed by id (preview, then add to chat)"

  async def execute(self, app, args: list[str]):
    try:
      if not args:
        await preview_then_append_chat_message(app, "Done", "Usage: /done <id>")
        return
      try:
        tid = int(args[0])
      except ValueError:
        await preview_then_append_chat_message(app, "Done", f"Invalid id: {args[0]!r}")
        return
      tt = _uc.get_todo_tools()
      result = await tt.update_todo_status(tid, "completed")
      if result.get("status") == "error":
        body = f"Error: {result.get('message', result)}"
      else:
        body = f"Marked todo **#{tid}** as completed."
      await preview_then_append_chat_message(app, "Todo updated", body)
    except Exception as e:
      print(f"done command failed: {e}")
