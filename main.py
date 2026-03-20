import os
import asyncio
from textual import on
from textual.app import App
from components.chat.chat import Chat, MsgBox
from textual.widgets import Header, Footer, Button, TabbedContent, TabPane
from components.sidebar.wrapper import Sidebar
from components.terminal.terminal_sidebar import TerminalSidebar, CustomTerminal
from components.utils.input_modal import InputModal
from textual.containers import Horizontal, Vertical

import utils.fs as fs
from utils.agent import Agent
from utils.cfg_man import cfg
from utils.db import db_manager
from components.sidebar.chat_history import ChatHistoryTab

from utils.theme_man import discover_themes

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('working_directory', type=str, help='The working directory', default='.')
args = parser.parse_args()

show_system_messages = cfg.get('interface.show_system_messages')
if args.working_directory == '.':
  args.working_directory = os.getcwd()
else:
  args.working_directory = args.working_directory

cfg.load_project_config(args.working_directory)
cfg.set('session.working_directory', args.working_directory)

from utils.git import ensure_git_repo
ensure_git_repo(args.working_directory)

from utils.skills import skill_manager
from utils.skill_components import discover_sidebar_tabs

skill_manager.discover_skills()
discover_sidebar_tabs()

_app_dir = os.path.dirname(os.path.abspath(__file__))
_css_paths = ['app.css'] + fs.discover_css(
  os.path.join(_app_dir, 'components'),
  relative_to=_app_dir
)
for _skill in skill_manager.skills.values():
  _skill_css_dir = os.path.join(_skill['base_dir'], 'components')
  if os.path.isdir(_skill_css_dir):
    _css_paths.extend(fs.discover_css(_skill_css_dir))

from utils.paths import get_tiered_paths
for tool_path in get_tiered_paths('tools', args.working_directory):
  if os.path.exists(tool_path):
    fs.load_folder(tool_path, '.py')

visibility = {
  'util-sidebar': cfg.get('interface.sidebar_open_on_start'),
  'term-sidebar': False
}

class TuiApp(App):
  BINDINGS = [
    ('ctrl+s', 'toggle_visible("util-sidebar")', 'Toggle Sidebar'),
    ('ctrl+t', 'toggle_visible("term-sidebar")', 'Toggle Terminal'),
    ('ctrl+w', 'close_chat_tab', 'Close Chat Tab'),
    ('ctrl+n', 'new_chat_tab', 'New Chat Tab'),
  ]
  CSS_PATH = _css_paths

  async def on_mount(self):
    themes = discover_themes()
    for t in themes.values():
      self.register_theme(t)
    self.theme = cfg.get('interface.theme', 'h4x0я')

  def watch_theme(self, theme: str) -> None:
    cfg.set('interface.theme', theme)

  async def cleanup(self):
    try:
      chat_widget = self.query_one(Chat)
      tabs = chat_widget.query_one("#chat_tabs", TabbedContent)
      for pane in tabs.query(TabPane):
        msg_box = pane.query_one(MsgBox)
        await msg_box.save_chat()
    except Exception:
      pass
    cfg.save()

  def compose(self):
    with Vertical():
      yield Header(show_clock=True)
      with Horizontal():
        side_classes = 'sidebar -visible' if cfg.get('interface.sidebar_open_on_start') else 'sidebar'
        yield Sidebar(id='util-sidebar', classes=side_classes)
        yield Chat(cfg)
        yield TerminalSidebar(id='term-sidebar', classes='right-sidebar')
      yield Footer()

  @on(ChatHistoryTab.ChatSelected)
  async def handle_chat_selected(self, event: ChatHistoryTab.ChatSelected):
    chat_widget = self.query_one(Chat)
    if event.chat_id is None:
        await chat_widget.add_chat_tab()
    else:
        chat_data = await db_manager.get_chat(event.chat_id)
        await chat_widget.add_chat_tab(event.chat_id, chat_data, event.title)

  def action_toggle_visible(self, id):
    visibility[id] = not visibility[id]
    widget = self.query_one(f'#{id}')
    widget.set_class(visibility[id], '-visible')
    if hasattr(widget, '_custom_bindings') and widget._custom_bindings:
      for binding in widget._custom_bindings:
        keys = binding[0]
        action = binding[1]
        desc = binding[2] if len(binding) > 2 else ""
        if visibility[id]:
          self.bind(keys, action, description=desc)
        elif hasattr(self, '_bindings') and keys in self._bindings.key_to_bindings:
          self._bindings.key_to_bindings[keys] = [
              b for b in self._bindings.key_to_bindings[keys] if b.action != action
          ]
          if not self._bindings.key_to_bindings[keys]:
              del self._bindings.key_to_bindings[keys]
      if hasattr(self, 'refresh_bindings'):
          self.refresh_bindings()
    if visibility[id] and id == 'term-sidebar':
        self.set_timer(0.05, widget.start_terminal)
        widget.query_one("#terminal_bash").focus()

  async def action_close_chat_tab(self):
    chat_widget = self.query_one(Chat)
    await chat_widget.close_current_tab()

  async def action_new_chat_tab(self):
    chat_widget = self.query_one(Chat)
    await chat_widget.add_chat_tab()

  def action_send_terminal_to_chat(self):
    self.trigger_send_terminal()

  @on(Button.Pressed, "#btn_send_terminal_chat")
  def on_send_terminal_chat(self, event: Button.Pressed):
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
            chat_widget = self.query_one(Chat)
            tabs = chat_widget.query_one("#chat_tabs", TabbedContent)
            active_pane = tabs.active
            if not active_pane:
                return
            chat_box = chat_widget.query_one(f"#{active_pane}", TabPane).query_one(MsgBox)
            
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


async def main():
  app = TuiApp()
  app.title = f"Cody - {cfg.get('session.working_directory')}"
  try:
    await app.run_async()
  finally:
    await app.cleanup()


if __name__ == "__main__":
  asyncio.run(main())