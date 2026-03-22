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


def _format_todos_for_scope(rows: list, title: str) -> str:
  if rows and isinstance(rows[0], dict) and rows[0].get("status") == "error":
    return f"Error ({title}): {rows[0].get('message', rows[0])}"
  if not rows:
    return f"### {title}\n\n(none)\n"
  lines = [f"### {title}\n"]
  for t in rows:
    tid = t.get("id")
    label = t.get("label", "")
    text = t.get("todo_text", "")
    st = t.get("status", "")
    lines.append(f"- **#{tid}** [{st}] {label}: {text}")
  lines.append("")
  return "\n".join(lines)


class TodosCommand(CommandBase):
  description = "List pending todos for project and global (preview, then add to chat)"

  async def execute(self, app, args: list[str]):
    try:
      tt = _uc.get_todo_tools()
      wd = cfg.get("session.working_directory", os.getcwd())
      project_rows = await tt.get_todos(scope=wd, status="pending")
      global_rows = await tt.get_todos(scope="global", status="pending")
      body = (
        _format_todos_for_scope(project_rows, f"Project ({wd})")
        + "\n"
        + _format_todos_for_scope(global_rows, "Global")
      )
      await preview_then_append_chat_message(app, "Todos (pending)", body.strip())
    except Exception as e:
      print(f"todos command failed: {e}")
