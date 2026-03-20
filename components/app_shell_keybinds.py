"""App-level keybindings for sidebars and terminal → chat (live outside main).

See workspace_app_mixin: do not subclass DOMNode here (breaks App CSS inheritance).
"""

from textual.widgets import TabPane

from components.chat.chat import ChatTab, MsgBox
from components.terminal.terminal_sidebar import CustomTerminal
from components.utils.input_modal import InputModal
from components.workspace.workspace import Workspace
from utils.cfg_man import cfg
from utils.layout_visibility import toggle_sidebar_on_app


class AppShellKeybindsMixin:
  BINDINGS = [
    ('ctrl+grave_accent', 'toggle_visible("util-sidebar")', 'Toggle Sidebar'),
    ('ctrl+t', 'toggle_visible("term-sidebar")', 'Toggle Terminal'),
  ]

  def action_toggle_visible(self, id):
    toggle_sidebar_on_app(self, id)

  def action_send_terminal_to_chat(self):
    self.trigger_send_terminal()

  def on_send_terminal_chat(self, event=None):
    self.trigger_send_terminal()

  def trigger_send_terminal(self):
    try:
      terminal = self.query_one("#terminal_bash", CustomTerminal)
      terminal_text = terminal.get_all_text()
    except Exception:
      return

    def check_modal_result(question: str | None):
      if question is None:
        return

      msg_content = ""
      if question.strip():
        msg_content += f"{question.strip()}\n\n"
      msg_content += f"```terminal\n{terminal_text}\n```"

      try:
        workspace = self.query_one(Workspace)
        active_pane = workspace.active_pane
        if not active_pane:
          return
        active_tab_id = active_pane.tabs.active
        if not active_tab_id:
          return

        active_tab = active_pane.tabs.query_one(f"#{active_tab_id}", TabPane)
        if not isinstance(active_tab, ChatTab):
          return

        chat_box = active_tab.query_one(MsgBox)

        msgs = [*chat_box.messages, {"role": "user", "content": msg_content}]
        placeholder_id = f"pending_{len(msgs)}"
        msgs.append({
          "id": placeholder_id,
          "role": "assistant",
          "content": "Thinking…",
          "loading": True,
        })

        chat_box.messages = msgs

        self.run_worker(
          chat_box.get_agent_response(msg_content, placeholder_id),
          exclusive=False,
        )
      except Exception as e:
        print(f"Failed to send to chat: {e}")

    self.push_screen(InputModal("Ask a question about the terminal context (optional)"), check_modal_result)
