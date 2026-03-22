import inspect

from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static

from utils.leader_registry import Handler, get_leader_root


class LeaderGuideScreen(ModalScreen[None]):
  """Bottom-right which-key style chord menu; Esc closes, Backspace pops one level."""

  BINDINGS = [
    Binding("escape", "close", "Close", show=False),
  ]
  CSS_PATH = "leader_guide_screen.css"

  def __init__(self) -> None:
    super().__init__()
    self._path: list[str] = []

  def compose(self) -> ComposeResult:
    with Vertical(id="leader_guide_panel"):
      yield Static("", id="leader_guide_path")
      yield Static("", id="leader_guide_options")

  def on_mount(self) -> None:
    panel = self.query_one("#leader_guide_panel")
    panel.can_focus = True
    self._refresh_display()
    panel.focus()

  def action_close(self) -> None:
    self.dismiss(None)

  def _current_node(self):
    node = get_leader_root()
    for k in self._path:
      nxt = node.children.get(k)
      if nxt is None:
        return node
      node = nxt
    return node

  def _refresh_display(self) -> None:
    path_el = self.query_one("#leader_guide_path", Static)
    opt_el = self.query_one("#leader_guide_options", Static)
    node = self._current_node()
    prefix = " ".join(self._path) if self._path else ""
    path_el.update(f"leader  {prefix}" if prefix else "leader")
    lines = []
    for key in sorted(node.children.keys()):
      child = node.children[key]
      desc = child.label or "(no label)"
      lines.append(f"  [b]{key}[/b]  {desc}")
    opt_el.update("\n".join(lines) if lines else "  (no bindings)")

  def _key_char(self, event: events.Key) -> str | None:
    if len(event.key) == 1 and event.key.isprintable():
      return event.key.lower()
    ch = getattr(event, "character", None)
    if ch and len(ch) == 1 and ch.isprintable():
      return ch.lower()
    return None

  async def _run_handler(self, handler: Handler) -> None:
    result = handler(self.app)
    if inspect.isawaitable(result):
      await result

  async def on_key(self, event: events.Key) -> None:
    if event.key in ("escape", "ctrl+c"):
      self.dismiss(None)
      event.prevent_default()
      event.stop()
      return
    if event.key == "backspace":
      if self._path:
        self._path.pop()
        self._refresh_display()
      event.prevent_default()
      event.stop()
      return

    kc = self._key_char(event)
    if not kc:
      return

    node = self._current_node()
    if kc not in node.children:
      event.prevent_default()
      event.stop()
      return

    child = node.children[kc]
    event.prevent_default()
    event.stop()

    if child.handler is not None:
      await self._run_handler(child.handler)
      self.dismiss(None)
      return

    self._path.append(kc)
    self._refresh_display()
