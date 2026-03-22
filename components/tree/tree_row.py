"""Generic tree row - single Horizontal, no nesting."""
from typing import Callable, Any

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.events import Click
from textual.message import Message
from textual.widgets import Button, Label
from textual.widget import Widget
from textual import on

from utils.icons import EXPAND_DOWN, EXPAND_RIGHT


class NodeToggled(Message, bubble=True):
  """Posted when an expandable row is clicked."""

  def __init__(self, node_id: Any):
    self.node_id = node_id
    super().__init__()


class NodeSelected(Message, bubble=True):
  """Posted when a non-expandable row is clicked."""

  def __init__(self, node_id: Any):
    self.node_id = node_id
    super().__init__()


class TreeRow(Widget):
  """Single row: indent + expand icon + node icon + label + buttons."""


  def __init__(
    self,
    node_id: Any,
    indent: str,
    is_expandable: bool,
    is_expanded: bool,
    display_name: str,
    icon: str,
    button_factory: Callable[[Any, bool], list[Button]],
    display_rich: Text | None = None,
    **kwargs,
  ):
    super().__init__(**kwargs)
    self.node_id = node_id
    self.indent = indent
    self.is_expandable = is_expandable
    self.is_expanded = is_expanded
    self.display_name = display_name
    self.icon = icon
    self.display_rich = display_rich
    self._button_factory = button_factory

  def compose(self) -> ComposeResult:
    expand = (EXPAND_DOWN + " ") if (self.is_expandable and self.is_expanded) else ((EXPAND_RIGHT + " ") if self.is_expandable else "  ")
    if self.display_rich is not None:
      label_content: str | Text = Text(self.icon + " ") + self.display_rich
    else:
      label_content = self.icon + " " + self.display_name

    with Horizontal():
      yield Label(self.indent, classes="tree-indent", markup=False)
      yield Label(expand, classes="tree-expand", markup=False)
      yield Label(label_content, classes="tree-label", markup=False)
      for btn in self._button_factory(self.node_id, self.is_expandable):
        yield btn

  @on(Click)
  def on_click(self, event: Click) -> None:
    if isinstance(event.control, Button):
      return
    event.stop()
    if self.is_expandable:
      self.post_message(NodeToggled(self.node_id))
    else:
      self.post_message(NodeSelected(self.node_id))
