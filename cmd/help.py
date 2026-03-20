from utils.cmd_loader import CommandBase

class HelpCommand(CommandBase):
    description = "Shows a list of available commands"

    async def execute(self, app, args: list[str]):
        # We can trigger a system message in the active chat
        try:
            # Find the active chat box
            from components.chat.chat import MsgBox
            from textual.widgets import TabbedContent
            
            tabs = app.query_one("#chat_tabs", TabbedContent)
            active_pane_id = tabs.active
            if not active_pane_id:
                return
                
            pane = tabs.get_pane(active_pane_id)
            msg_box = pane.query_one(MsgBox)
            
            # Get the commands from the input box
            from components.chat.input import MessageInput
            input_box = msg_box.query_one(MessageInput)
            
            help_text = "### Available Commands\n\n"
            for cmd_name, cmd_obj in input_box.commands.items():
                help_text += f"- `/{cmd_name}`: {cmd_obj.description}\n"
                
            # Add a system message
            msgs = [*msg_box.messages, {
                "role": "system",
                "content": help_text
            }]
            msg_box.messages = msgs
            
            # Update the actor's memory too so it persists
            msg_box.actor.add_msg("system", help_text)
            
        except Exception as e:
            print(f"Help command failed: {e}")
