"""Generic tree row - single Horizontal, no nesting."""
from typing import Callable, Any

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

  DEFAULT_CSS = """
  TreeRow {
    height: 1;
    width: 100%;
  }
  TreeRow:hover {
    background: $surface-lighten-2;
  }

  TreeRow .tree-indent {
    width: auto;
  }

  TreeRow .tree-label {
    width: 1fr;
  }

  TreeRow .tree-node-btn {
    min-width: 3;
    height: 2;
    padding: 0 1;
    color: $primary-lighten-2;
    align: right middle;
  }
  """

  def __init__(
    self,
    node_id: Any,
    indent: str,
    is_expandable: bool,
    is_expanded: bool,
    display_name: str,
    icon: str,
    button_factory: Callable[[Any, bool], list[Button]],
    **kwargs,
  ):
    super().__init__(**kwargs)
    self.node_id = node_id
    self.indent = indent
    self.is_expandable = is_expandable
    self.is_expanded = is_expanded
    self.display_name = display_name
    self.icon = icon
    self._button_factory = button_factory

  def compose(self) -> ComposeResult:
    expand = (EXPAND_DOWN + " ") if (self.is_expandable and self.is_expanded) else ((EXPAND_RIGHT + " ") if self.is_expandable else "  ")
    label_text = self.icon + " " + self.display_name

    with Horizontal():
      yield Label(self.indent, classes="tree-indent")
      yield Label(expand, classes="tree-expand")
      yield Label(label_text, classes="tree-label")
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
