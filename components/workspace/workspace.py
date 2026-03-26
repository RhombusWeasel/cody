from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import TabPane

from components.tabs import TabContainer
from textual.widget import Widget
from textual.reactive import reactive
from textual import on
from textual.events import Click

if TYPE_CHECKING:
  from utils.leader_registry import LeaderRegistrar


def pane_containing(widget: Widget) -> Pane | None:
  """Return the workspace Pane ancestor of a widget, if any."""
  for w in widget.ancestors:
    if isinstance(w, Pane):
      return w
  return None


def _horizontal_row_columns(row: Horizontal) -> list[list[Pane]]:
  """Columns of a row split: each child is one column (Pane or subtree with panes)."""
  columns: list[list[Pane]] = []
  for child in row.children:
    if isinstance(child, Pane):
      col = [child]
    else:
      col = list(child.query(Pane))
    if col:
      columns.append(col)
  return columns


def _pane_row_column_index(columns: list[list[Pane]], pane: Pane) -> int | None:
  for i, col in enumerate(columns):
    if pane in col:
      return i
  return None


def _vertical_stack_rows(stack: Vertical) -> list[list[Pane]]:
  """Rows of a vertical stack: each child is one band (Pane or subtree with panes)."""
  rows: list[list[Pane]] = []
  for child in stack.children:
    if isinstance(child, Pane):
      band = [child]
    else:
      band = list(child.query(Pane))
    if band:
      rows.append(band)
  return rows


def _pane_stack_row_index(rows: list[list[Pane]], pane: Pane) -> int | None:
  for i, band in enumerate(rows):
    if pane in band:
      return i
  return None


def _reparent_preserving_children(child: Widget, new_parent: Widget) -> None:
    """Move child to new_parent without Widget.remove() (remove prunes composed subtree)."""
    old_parent = child._parent
    if old_parent is None:
        return
    old_parent._nodes._remove(child)
    child._detach()
    new_parent._nodes._append(child)
    child._attach(new_parent)
    old_parent.refresh(layout=True)
    new_parent.refresh(layout=True)


class Pane(Widget):
    """A single pane in the workspace, containing a TabContainer."""

    def __init__(self, workspace, **kwargs):
        super().__init__(**kwargs)
        self.workspace = workspace
        self.can_focus = True

    def compose(self) -> ComposeResult:
        yield TabContainer()

    @property
    def tabs(self) -> TabContainer:
        return self.query_one(TabContainer)

    async def add_tab(self, tab: TabPane, set_active: bool = True):
        await self.tabs.add_pane(tab)
        if set_active:
            self.tabs.active = tab.id

    async def close_active_tab(self):
        active = self.tabs.active
        if active:
            await self.tabs.remove_pane(active)
            if not self.tabs.active and len(list(self.tabs.query(TabPane))) == 0:
                # If no tabs left, we might want to close the pane if it's not the only one
                await self.workspace.check_empty_pane(self)

    def on_click(self, event: Click) -> None:
        self.workspace.set_active_pane(self)
        target = event.control
        if target is not None and self in target.ancestors:
            return
        self.focus()

    def on_focus(self) -> None:
        self.workspace.set_active_pane(self)
        self.add_class("-active-pane")

    def on_blur(self) -> None:
        self.remove_class("-active-pane")


class Workspace(Widget):
    """The root workspace container managing panes and splits."""

    BINDINGS = [
        Binding("ctrl+h", "focus_pane_left", "", show=False),
        Binding("ctrl+l", "focus_pane_right", "", show=False),
        Binding("ctrl+k", "focus_pane_up", "", show=False),
        Binding("ctrl+j", "focus_pane_down", "", show=False),
    ]

    active_pane: Pane | None = reactive(None)

    def compose(self) -> ComposeResult:
        # Start with a single pane in a horizontal container
        with Horizontal(id="workspace_root"):
            yield Pane(self, id="initial_pane")

    def on_mount(self):
        initial_pane = self.query_one("#initial_pane", Pane)
        self.set_active_pane(initial_pane)

    def set_active_pane(self, pane: Pane):
        if self.active_pane and self.active_pane != pane:
            self.active_pane.remove_class("-active-pane")
        self.active_pane = pane
        self.active_pane.add_class("-active-pane")

    async def add_tab(self, tab: TabPane, set_active: bool = True):
        if not self.active_pane:
            panes = list(self.query(Pane))
            if panes:
                self.set_active_pane(panes[0])
        if self.active_pane:
            await self.active_pane.add_tab(tab, set_active)

    async def close_active_tab(self):
        if self.active_pane:
            await self.active_pane.close_active_tab()

    async def check_empty_pane(self, pane: Pane):
        panes = list(self.query(Pane))
        if len(panes) > 1:
            await pane.remove()
            # If parent is now empty or has 1 child, we might want to flatten it, 
            # but for now Textual handles empty containers fine.
            # Set active pane to another one
            remaining = list(self.query(Pane))
            if remaining:
                self.set_active_pane(remaining[0])

    async def close_active_pane(self):
        """Remove the active pane when there is more than one (splits)."""
        if not self.active_pane:
            return
        panes = list(self.query(Pane))
        if len(panes) <= 1:
            return
        current = self.active_pane
        try:
            idx = panes.index(current)
        except ValueError:
            return
        if idx < len(panes) - 1:
            target = panes[idx + 1]
        else:
            target = panes[idx - 1]
        await current.remove()
        self.set_active_pane(target)
        target.focus()

    async def split_vertical(self):
        """Split the active pane vertically (side-by-side, so a Horizontal container)."""
        if not self.active_pane:
            return
        
        parent = self.active_pane.parent
        new_pane = Pane(self)
        
        if isinstance(parent, Horizontal):
            await parent.mount(new_pane, after=self.active_pane)
        else:
            old_pane = self.active_pane
            h_container = Horizontal(classes="workspace-split-row")
            await parent.mount(h_container, after=old_pane)
            _reparent_preserving_children(old_pane, h_container)
            await h_container.mount(new_pane)
            
        self.set_active_pane(new_pane)

    async def split_horizontal(self):
        """Split the active pane horizontally (top-bottom, so a Vertical container)."""
        if not self.active_pane:
            return
        
        parent = self.active_pane.parent
        new_pane = Pane(self)
        
        if isinstance(parent, Vertical):
            await parent.mount(new_pane, after=self.active_pane)
        else:
            old_pane = self.active_pane
            v_container = Vertical(classes="workspace-split-stack")
            await parent.mount(v_container, after=old_pane)
            _reparent_preserving_children(old_pane, v_container)
            await v_container.mount(new_pane)
            
        self.set_active_pane(new_pane)

    def _focus_pane_horizontal_across_rows(self, pane: Pane, delta: int) -> None:
        """Move across row columns (side-by-side); walk up at column edges; wrap within innermost row if needed."""
        horizontals: list[Horizontal] = []
        node = pane.parent
        while node is not None:
            if isinstance(node, Horizontal):
                horizontals.append(node)
            node = node.parent

        for h in horizontals:
            columns = _horizontal_row_columns(h)
            if len(columns) < 2:
                continue
            col_idx = _pane_row_column_index(columns, pane)
            if col_idx is None:
                continue
            new_idx = col_idx + delta
            if 0 <= new_idx < len(columns):
                target = columns[new_idx][0]
                self.set_active_pane(target)
                target.focus()
                return

        for h in horizontals:
            columns = _horizontal_row_columns(h)
            if len(columns) < 2:
                continue
            col_idx = _pane_row_column_index(columns, pane)
            if col_idx is None:
                continue
            new_idx = (col_idx + delta) % len(columns)
            target = columns[new_idx][0]
            self.set_active_pane(target)
            target.focus()
            return

    def _focus_pane_vertical_across_stacks(self, pane: Pane, delta: int) -> None:
        """Move across vertical stack bands; walk up at edges; wrap innermost stack if needed."""
        verticals: list[Vertical] = []
        node = pane.parent
        while node is not None:
            if isinstance(node, Vertical):
                verticals.append(node)
            node = node.parent

        for v in verticals:
            rows = _vertical_stack_rows(v)
            if len(rows) < 2:
                continue
            row_idx = _pane_stack_row_index(rows, pane)
            if row_idx is None:
                continue
            new_idx = row_idx + delta
            if 0 <= new_idx < len(rows):
                target = rows[new_idx][0]
                self.set_active_pane(target)
                target.focus()
                return

        for v in verticals:
            rows = _vertical_stack_rows(v)
            if len(rows) < 2:
                continue
            row_idx = _pane_stack_row_index(rows, pane)
            if row_idx is None:
                continue
            new_idx = (row_idx + delta) % len(rows)
            target = rows[new_idx][0]
            self.set_active_pane(target)
            target.focus()
            return

    def action_focus_pane_left(self) -> None:
        if not self.active_pane:
            return
        self._focus_pane_horizontal_across_rows(self.active_pane, -1)

    def action_focus_pane_right(self) -> None:
        if not self.active_pane:
            return
        self._focus_pane_horizontal_across_rows(self.active_pane, 1)

    def action_focus_pane_up(self) -> None:
        if not self.active_pane:
            return
        self._focus_pane_vertical_across_stacks(self.active_pane, -1)

    def action_focus_pane_down(self) -> None:
        if not self.active_pane:
            return
        self._focus_pane_vertical_across_stacks(self.active_pane, 1)

    def focus_next_pane(self):
        panes = list(self.query(Pane))
        if not panes:
            return
        if not self.active_pane:
            self.set_active_pane(panes[0])
            return
        
        try:
            idx = panes.index(self.active_pane)
            next_idx = (idx + 1) % len(panes)
            self.set_active_pane(panes[next_idx])
            self.active_pane.focus()
        except ValueError:
            self.set_active_pane(panes[0])

    def focus_previous_pane(self):
        panes = list(self.query(Pane))
        if not panes:
            return
        if not self.active_pane:
            self.set_active_pane(panes[0])
            return
        
        try:
            idx = panes.index(self.active_pane)
            prev_idx = (idx - 1) % len(panes)
            self.set_active_pane(panes[prev_idx])
            self.active_pane.focus()
        except ValueError:
            self.set_active_pane(panes[-1])

    def get_active_msg_box(self):
        """Return MsgBox for the active pane's active chat tab, or None."""
        from components.chat.chat import MsgBox

        if not self.active_pane:
            return None
        active_tab_id = self.active_pane.tabs.active
        if not active_tab_id:
            return None
        try:
            tab = self.active_pane.tabs.query_one(f"#{active_tab_id}", TabPane)
            return tab.query_one(MsgBox)
        except Exception:
            return None


def register_leader_chords(reg: LeaderRegistrar) -> None:
    """Leader menu: Window — splits, close pane, focus panes (see chat for tab actions)."""
    from textual.app import App as TextualApp

    async def split_vertical(app: TextualApp) -> None:
        ws = app.query_one(Workspace)
        await ws.split_vertical()

    async def split_horizontal(app: TextualApp) -> None:
        ws = app.query_one(Workspace)
        await ws.split_horizontal()

    async def close_pane(app: TextualApp) -> None:
        ws = app.query_one(Workspace)
        await ws.close_active_pane()

    async def focus_next(app: TextualApp) -> None:
        ws = app.query_one(Workspace)
        ws.focus_next_pane()

    async def focus_prev(app: TextualApp) -> None:
        ws = app.query_one(Workspace)
        ws.focus_previous_pane()

    reg.add_submenu((), "w", "Window")
    reg.add_action(("w",), "v", "Split vertical", split_vertical)
    reg.add_action(("w",), "h", "Split horizontal", split_horizontal)
    reg.add_action(("w",), "q", "Close pane (split)", close_pane)
    reg.add_action(("w",), "l", "Focus next pane", focus_next)
    reg.add_action(("w",), "r", "Focus previous pane", focus_prev)
