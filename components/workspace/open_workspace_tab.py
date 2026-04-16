"""Message for skills/sidebars to open or focus a workspace TabPane."""
from __future__ import annotations

from textual.message import Message
from textual.widgets import TabPane


class OpenWorkspaceTab(Message):
  """Request the app to add `tab` to the workspace, or focus an existing TabPane with the same id."""

  def __init__(self, tab: TabPane) -> None:
    self.tab = tab
    super().__init__()
