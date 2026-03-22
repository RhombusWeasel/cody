"""Scrollable body region: vertical stack with ContentSwitcher for tab panes."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import ContentSwitcher


class TabBody(Vertical):
  """Fills remaining space; holds the ContentSwitcher for TabPane bodies."""

  DEFAULT_CSS = """
  TabBody {
    height: 1fr;
    min-height: 0;
    width: 1fr;
  }
  TabBody ContentSwitcher {
    height: 1fr;
    min-height: 0;
    width: 1fr;
  }
  """

  def compose(self) -> ComposeResult:
    yield ContentSwitcher()
