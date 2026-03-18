from utils.cmd_loader import CommandBase

class EchoCommand(CommandBase):
    description = "Echoes the given text as a system message"

    async def execute(self, app, args: list[str]):
        try:
            from components.chat.chat import MsgBox
            from textual.widgets import TabbedContent

            text = " ".join(args) if args else "(nothing)"
            tabs = app.query_one("#chat_tabs", TabbedContent)
            if not tabs.active:
                return
            pane = tabs.get_pane(tabs.active)
            msg_box = pane.query_one(MsgBox)
            msg_box.messages = [*msg_box.messages, {"role": "system", "content": text}]
        except Exception as e:
            print(f"Echo command failed: {e}")
