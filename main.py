import argparse
import asyncio
import os

parser = argparse.ArgumentParser()
parser.add_argument(
  'working_directory',
  nargs='?',
  default='.',
  type=str,
  help='The working directory',
)
parser.add_argument(
  '--encrypt-config',
  action='store_true',
  help='Encrypt plaintext JSON configs to .enc (PBKDF2+Fernet), then exit.',
)
parser.add_argument(
  '--config-password-file',
  default=None,
  metavar='PATH',
  help='Read config decryption password from file (non-interactive).',
)
args = parser.parse_args()

args.working_directory = os.path.abspath(
  os.getcwd() if args.working_directory == '.' else args.working_directory
)

from utils.cfg_man import cfg, ensure_config_loaded

ensure_config_loaded(
  args.working_directory,
  encrypt_config=args.encrypt_config,
  config_password_file=args.config_password_file,
)

from textual import on
from textual.app import App
from components.chat.chat import ChatTab, MsgBox
from components.workspace.workspace import Workspace
from textual.widgets import Header, Footer, TabPane
from components.sidebar.wrapper import Sidebar
from components.terminal.terminal_sidebar import TerminalSidebar
from textual.containers import Horizontal, Vertical

import utils.fs as fs
from utils.db import db_manager
from components.sidebar.chat_history import ChatHistoryTab, OpenChatWithSeedMessage

from utils.theme_man import discover_themes

from components.workspace.workspace_app_mixin import WorkspaceAppKeybindsMixin
from components.app_shell_keybinds import AppShellKeybindsMixin
from utils.layout_visibility import init_sidebar_state_from_cfg

cfg.set('session.working_directory', args.working_directory)
init_sidebar_state_from_cfg()

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


# Keybind mixins must not subclass DOMNode if they appear before App: _css_bases would skip App
# and drop its DEFAULT_CSS. Merge BINDINGS explicitly instead of relying on _merge_bindings.
class TuiApp(WorkspaceAppKeybindsMixin, AppShellKeybindsMixin, App):
  BINDINGS = [
    *AppShellKeybindsMixin.BINDINGS,
    *WorkspaceAppKeybindsMixin.BINDINGS,
  ]
  CSS_PATH = _css_paths

  async def on_mount(self):
    themes = discover_themes()
    for t in themes.values():
      self.register_theme(t)
    self.theme = cfg.get('interface.theme', 'h4x0я')
    # Start with an initial chat tab
    await self.action_new_chat_tab()

  def watch_theme(self, theme: str) -> None:
    cfg.set('interface.theme', theme)

  async def cleanup(self):
    try:
      workspace = self.query_one(Workspace)
      for msg_box in workspace.query(MsgBox):
        await msg_box.save_chat()
    except Exception:
      pass
    cfg.save()

  def compose(self):
    with Vertical(id="app_body"):
      yield Header(show_clock=True)
      with Horizontal(id="main_row"):
        side_classes = 'sidebar -visible' if cfg.get('interface.sidebar_open_on_start') else 'sidebar'
        yield Sidebar(id='util-sidebar', classes=side_classes)
        yield Workspace(id="workspace")
        yield TerminalSidebar(id='term-sidebar', classes='right-sidebar')
      yield Footer()

  @on(ChatHistoryTab.ChatSelected)
  async def handle_chat_selected(self, event: ChatHistoryTab.ChatSelected):
    workspace = self.query_one(Workspace)
    if event.chat_id is None:
        await workspace.add_tab(ChatTab(cfg))
    else:
        # Check if already open
        for tab in workspace.query(ChatTab):
            if tab.chat_id == event.chat_id:
                # Focus this tab's pane and set it active
                pane = tab.parent.parent # TabPane -> TabbedContent -> Pane
                workspace.set_active_pane(pane)
                pane.tabs.active = tab.id
                return
        chat_data = await db_manager.get_chat(event.chat_id)
        await workspace.add_tab(ChatTab(cfg, chat_id=event.chat_id, chat_data=chat_data, title=event.title))

  @on(OpenChatWithSeedMessage)
  async def handle_open_chat_with_seed(self, event: OpenChatWithSeedMessage) -> None:
    workspace = self.query_one(Workspace)
    tab = ChatTab(cfg)
    await workspace.add_tab(tab)

    def run_seed() -> None:
      msg_box = tab.query_one(MsgBox)
      msg_box.run_conversation_from_text(event.user_message)

    tab.call_later(run_seed)


async def main():
  app = TuiApp()
  app.title = f"Cody - {cfg.get('session.working_directory')}"
  try:
    await app.run_async()
  finally:
    await app.cleanup()


if __name__ == "__main__":
  asyncio.run(main())
