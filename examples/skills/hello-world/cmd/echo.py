from utils.cmd_loader import CommandBase
from components.utils.input_modal import preview_then_append_chat_message


class EchoCommand(CommandBase):
  description = "Echo text in a preview modal; add to chat or cancel"

  async def execute(self, app, args: list[str]):
    try:
      text = " ".join(args) if args else "(nothing)"
      await preview_then_append_chat_message(app, "Echo", text)
    except Exception as e:
      print(f"Echo command failed: {e}")
