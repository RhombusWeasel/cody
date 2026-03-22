"""Per-tab title row: label selects tab, close removes it."""

from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.content import ContentType
from textual.events import Click
from textual.message import Message
from textual.widgets import Button, Label


def _safe_dom_id_fragment(pane_id: str) -> str:
  return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in pane_id)


class TabTitle(Horizontal):
  """One tab in the header: clickable title label and close control."""

  class CloseRequested(Message):
    """Posted when the user clicks the close button."""

    bubble = True

    def __init__(self, pane_id: str) -> None:
      self.pane_id = pane_id
      super().__init__()

  def __init__(self, pane_id: str, title: ContentType, **kwargs) -> None:
    self.pane_id = pane_id
    self._title = title
    safe = _safe_dom_id_fragment(pane_id)
    kwargs.setdefault("classes", "tab-title")
    kwargs.setdefault("id", f"title-{safe}")
    super().__init__(**kwargs)

  def compose(self) -> ComposeResult:
    yield Label(self._title, classes="tab-title-label")
    yield Button(
      "×",
      classes="tab-title-close",
      flat=True,
      compact=True,
    )

  @on(Button.Pressed, ".tab-title-close")
  def _close_pressed(self) -> None:
    self.post_message(self.CloseRequested(self.pane_id))

  def on_click(self, event: Click) -> None:
    if event.control is None:
      return
    if "tab-title-close" in event.control.classes:
      return
    container = self._tab_container()
    if container is not None:
      container.active = self.pane_id

  def _tab_container(self):
    from components.tabs.tab_container import TabContainer

    for node in self.ancestors:
      if isinstance(node, TabContainer):
        return node
    return None
