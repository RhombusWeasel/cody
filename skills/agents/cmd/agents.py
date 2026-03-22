import sqlite3

from utils.cmd_loader import CommandBase
from utils.db import db_manager
from components.utils.input_modal import preview_then_append_chat_message


class AgentsCommand(CommandBase):
  description = "List configured sub-agents (preview, then add to chat)"

  async def execute(self, app, args: list[str]):
    try:
      conn = sqlite3.connect(db_manager.get_project_db_path())
      cursor = conn.cursor()
      cursor.execute("SELECT name, description, provider, model FROM agents ORDER BY name")
      rows = cursor.fetchall()
      conn.close()
      if not rows:
        body = "No agents defined. Create agents via the Agents sidebar tab."
      else:
        parts: list[str] = []
        for name, description, provider, model in rows:
          provider_str = f" [{provider or 'default'}/{model or 'default'}]" if provider or model else ""
          parts.append(f"{name}{provider_str}")
          if description:
            parts.append(f"  {description}")
          parts.append("")
        body = "\n".join(parts).rstrip()
      await preview_then_append_chat_message(app, "Agents", body)
    except Exception as e:
      print(f"agents command failed: {e}")
