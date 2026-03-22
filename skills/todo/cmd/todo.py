import importlib.util
import os

from utils.cmd_loader import CommandBase
from utils.cfg_man import cfg
from components.utils.input_modal import preview_then_append_chat_message

_cmd_dir = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("_todo_cmd_common", os.path.join(_cmd_dir, "__todo_common.py"))
_uc = importlib.util.module_from_spec(_spec)
assert _spec.loader
_spec.loader.exec_module(_uc)


class TodoCommand(CommandBase):
  description = "Add a todo: /todo [global] <label> [details…] (preview, then add to chat)"

  async def execute(self, app, args: list[str]):
    try:
      if not args:
        await preview_then_append_chat_message(
          app,
          "Todo",
          "Usage: /todo [global] <label> [description]",
        )
        return
      tt = _uc.get_todo_tools()
      wd = cfg.get("session.working_directory", os.getcwd())
      rest = list(args)
      scope = wd
      if rest[0] == "global":
        scope = "global"
        rest = rest[1:]
      if not rest:
        await preview_then_append_chat_message(app, "Todo", "Usage: /todo [global] <label> [description]")
        return
      label = rest[0]
      todo_text = " ".join(rest[1:]).strip() or label
      result = await tt.add_todo(label=label, scope=scope, todo_text=todo_text, deadline=None)
      if result.get("status") == "error":
        body = f"Error: {result.get('message', result)}"
      else:
        body = f"Created todo **#{result.get('id')}** — **{label}** ({scope})\n\n{todo_text}"
      await preview_then_append_chat_message(app, "Todo added", body)
    except Exception as e:
      print(f"todo command failed: {e}")
