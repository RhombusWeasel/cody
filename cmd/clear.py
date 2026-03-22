from utils.cmd_loader import CommandBase


class ClearCommand(CommandBase):
  description = "Clears the current chat history"

  async def execute(self, app, args: list[str]):
    try:
      from components.chat.input import MessageInput
      from components.workspace.workspace import Workspace
      from utils.agent import Agent

      workspace = app.query_one(Workspace)
      msg_box = workspace.get_active_msg_box()
      if not msg_box:
        return

      new_agent = Agent()
      msg_box.actor = new_agent
      msg_box.query_one(MessageInput).actor = new_agent

      show_system = msg_box.config.get("interface.show_system_messages", False)
      msg_box.messages = (
        new_agent.msg if show_system else [m for m in new_agent.msg if m.get("role") != "system"]
      )

      await msg_box.save_chat()
    except Exception as e:
      print(f"Clear command failed: {e}")
