from utils.cmd_loader import CommandBase


class HelpCommand(CommandBase):
  description = "Shows a list of available commands"

  async def execute(self, app, args: list[str]):
    try:
      from components.chat.input import MessageInput
      from components.utils.commands_help_modal import CommandsHelpModal
      from components.workspace.workspace import Workspace

      workspace = app.query_one(Workspace)
      msg_box = workspace.get_active_msg_box()
      if not msg_box:
        return

      input_box = msg_box.query_one(MessageInput)
      help_text = "### Available Commands\n\n"
      for cmd_name, cmd_obj in input_box.commands.items():
        help_text += f"- `/{cmd_name}`: {cmd_obj.description}\n"

      app.push_screen(CommandsHelpModal(help_text))
    except Exception as e:
      print(f"Help command failed: {e}")
