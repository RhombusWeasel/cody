from utils.cmd_loader import CommandBase

class ClearCommand(CommandBase):
    description = "Clears the current chat history"

    async def execute(self, app, args: list[str]):
        try:
            from components.chat.chat import MsgBox
            from textual.widgets import TabbedContent
            
            tabs = app.query_one("#chat_tabs", TabbedContent)
            active_pane_id = tabs.active
            if not active_pane_id:
                return
                
            pane = tabs.get_pane(active_pane_id)
            msg_box = pane.query_one(MsgBox)
            
            # Clear messages
            msg_box.messages = []
            msg_box.actor.msg = []
            
            # Save the cleared chat
            await msg_box.save_chat()
            
        except Exception as e:
            print(f"Clear command failed: {e}")
