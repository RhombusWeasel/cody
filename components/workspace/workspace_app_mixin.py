"""App-level keybindings that delegate to Workspace (priority=True for TextArea focus).

Do not subclass DOMNode/Widget here: if this mixin is listed before App on TuiApp, Textual's
_css_bases would follow Mixin→DOMNode and skip App, dropping App DEFAULT_CSS (broken UI).
"""

from textual.binding import Binding
from textual.widgets import TabPane

from components.chat.chat import ChatTab
from components.workspace.editor_tab import EditorTab
from components.workspace.workspace import Workspace
from utils.cfg_man import cfg


class WorkspaceAppKeybindsMixin:
  # priority=True so split/pane keys still fire while MessageInput (TextArea) or editors are focused.
  BINDINGS = [
    Binding('ctrl+w', 'close_active_tab', 'Close Tab', priority=True),
    Binding('ctrl+shift+p', 'close_active_pane', 'Close Pane', priority=True),
    Binding('ctrl+n', 'new_chat_tab', 'New Chat Tab', priority=True),
    Binding('ctrl+v', 'split_vertical', 'Split Vertical', priority=True),
    Binding('ctrl+h', 'split_horizontal', 'Split Horizontal', priority=True),
    Binding('ctrl+right', 'focus_next_pane', 'Next Pane', priority=True),
    Binding('ctrl+left', 'focus_previous_pane', 'Previous Pane', priority=True),
    Binding('ctrl+s', 'save_active_editor', 'Save File', priority=True),
  ]

  async def action_close_active_tab(self):
    workspace = self.query_one(Workspace)
    await workspace.close_active_tab()

  async def action_close_active_pane(self):
    workspace = self.query_one(Workspace)
    await workspace.close_active_pane()

  async def action_new_chat_tab(self):
    workspace = self.query_one(Workspace)
    await workspace.add_tab(ChatTab(cfg))

  async def action_split_vertical(self):
    workspace = self.query_one(Workspace)
    await workspace.split_vertical()

  async def action_split_horizontal(self):
    workspace = self.query_one(Workspace)
    await workspace.split_horizontal()

  def action_focus_next_pane(self):
    workspace = self.query_one(Workspace)
    workspace.focus_next_pane()

  def action_focus_previous_pane(self):
    workspace = self.query_one(Workspace)
    workspace.focus_previous_pane()

  def action_save_active_editor(self):
    try:
      workspace = self.query_one(Workspace)
      active_pane = workspace.active_pane
      if not active_pane:
        return
      active_tab_id = active_pane.tabs.active
      if not active_tab_id:
        return
      active_tab = active_pane.tabs.query_one(f"#{active_tab_id}", TabPane)
      if isinstance(active_tab, EditorTab):
        active_tab.action_save_file()
    except Exception:
      pass
