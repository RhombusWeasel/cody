from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import TabbedContent, TabPane
from textual.widget import Widget
from textual.reactive import reactive
from textual import on
from textual.events import Click

class Pane(Widget):
    """A single pane in the workspace, containing a TabbedContent."""
    
    def __init__(self, workspace, **kwargs):
        super().__init__(**kwargs)
        self.workspace = workspace
        self.can_focus = True

    def compose(self) -> ComposeResult:
        yield TabbedContent()

    @property
    def tabs(self) -> TabbedContent:
        return self.query_one(TabbedContent)

    async def add_tab(self, tab: TabPane, set_active: bool = True):
        await self.tabs.add_pane(tab)
        if set_active:
            self.tabs.active = tab.id

    async def close_active_tab(self):
        active = self.tabs.active
        if active:
            await self.tabs.remove_pane(active)
            if self.tabs.active is None and len(list(self.tabs.query(TabPane))) == 0:
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
            await old_pane.remove()
            await h_container.mount(old_pane)
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
            await old_pane.remove()
            await v_container.mount(old_pane)
            await v_container.mount(new_pane)
            
        self.set_active_pane(new_pane)

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
