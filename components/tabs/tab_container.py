"""Workspace-style tab container: custom header + ContentSwitcher bodies (TabPane)."""

from __future__ import annotations

from typing import Iterable

from textual import on
from textual.app import ComposeResult
from textual.await_complete import AwaitComplete
from textual.containers import Horizontal, Vertical
from textual.css.query import NoMatches
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import ContentSwitcher, TabPane

from components.tabs.body import TabBody
from components.tabs.header import TabHeader
from components.tabs.title_button import TabTitle


class TabContainer(Widget):
  """Tabbed UI like TabbedContent: TabPane bodies in a ContentSwitcher, custom tab row."""

  active: reactive[str] = reactive("", init=False)

  def __init__(
    self,
    *,
    title_bar: Horizontal | None = None,
    title_trailing: Iterable[Widget] | None = None,
    name: str | None = None,
    id: str | None = None,
    classes: str | None = None,
    disabled: bool = False,
  ) -> None:
    self._title_bar_supplied = title_bar
    self._title_trailing = tuple(title_trailing or ())
    self._tab_counter = 0
    super().__init__(name=name, id=id, classes=classes, disabled=disabled)

  def compose(self) -> ComposeResult:
    with Vertical():
      if self._title_bar_supplied is not None:
        yield self._title_bar_supplied
      else:
        with Horizontal(classes="tab-container-title-row"):
          yield TabHeader(id="tab-header")
          for w in self._title_trailing:
            yield w
      yield TabBody()

  async def on_mount(self) -> None:
    if self._title_bar_supplied is not None:
      await self._title_bar_supplied.mount(TabHeader(id="tab-header"), before=0)

  @property
  def _switcher(self) -> ContentSwitcher:
    return self.query_one(TabBody).query_one(ContentSwitcher)

  def _header(self) -> TabHeader:
    return self.query_one(TabHeader)

  @property
  def active_pane(self) -> TabPane | None:
    aid = self.active
    if not aid:
      return None
    try:
      p = self._switcher.get_child_by_id(aid, expect_type=TabPane)
    except NoMatches:
      return None
    return p

  def get_pane(self, pane_id: str) -> TabPane:
    return self._switcher.get_child_by_id(pane_id, expect_type=TabPane)

  def _ensure_pane_id(self, pane: TabPane) -> TabPane:
    if pane.id is None:
      self._tab_counter += 1
      pane.id = f"tab-{self._tab_counter}"
    return pane

  def _find_tab_title(self, header: TabHeader, pane_id: str) -> TabTitle | None:
    for t in header.query(TabTitle):
      if t.pane_id == pane_id:
        return t
    return None

  def add_pane(
    self,
    pane: TabPane,
    *,
    before: TabPane | str | None = None,
    after: TabPane | str | None = None,
  ) -> AwaitComplete:
    if before is not None and after is not None:
      raise ValueError("Only one of before or after may be set")
    if isinstance(before, TabPane):
      before = before.id
    if isinstance(after, TabPane):
      after = after.id
    pane = self._ensure_pane_id(pane)
    assert pane.id is not None
    pane.display = False

    async def _go() -> None:
      switcher = self._switcher
      header = self._header()
      title = TabTitle(pane.id, pane._title)
      before_w = after_w = None
      before_t = after_t = None
      if before:
        try:
          before_w = switcher.get_child_by_id(before)
          before_t = self._find_tab_title(header, before)
        except NoMatches:
          pass
      if after:
        try:
          after_w = switcher.get_child_by_id(after)
          after_t = self._find_tab_title(header, after)
        except NoMatches:
          pass
      await switcher.mount(pane, before=before_w, after=after_w)
      await header.mount(title, before=before_t, after=after_t)
      self._refresh_title_styles()

    return AwaitComplete(_go())

  def remove_pane(self, pane_id: str) -> AwaitComplete:
    async def _go() -> None:
      header = self._header()
      switcher = self._switcher
      order = [t.pane_id for t in header.query(TabTitle)]
      try:
        idx = order.index(pane_id)
      except ValueError:
        idx = -1
      was_active = self.active == pane_id
      next_id = ""
      if was_active and idx >= 0:
        if idx + 1 < len(order):
          next_id = order[idx + 1]
        elif idx - 1 >= 0:
          next_id = order[idx - 1]
      try:
        title = self._find_tab_title(header, pane_id)
        if title is not None:
          await title.remove()
      except NoMatches:
        pass
      try:
        node = switcher.get_child_by_id(pane_id)
        await node.remove()
      except NoMatches:
        pass
      if was_active:
        remaining = [t.pane_id for t in header.query(TabTitle)]
        if not remaining:
          self.active = ""
        elif next_id and next_id in remaining:
          self.active = next_id
        else:
          self.active = remaining[0]
      self._refresh_title_styles()

    return AwaitComplete(_go())

  def _watch_active(self, active: str) -> None:
    sw = self._switcher
    sw.current = active if active else None
    self._refresh_title_styles()

  def _refresh_title_styles(self) -> None:
    try:
      header = self._header()
    except NoMatches:
      return
    for t in header.query(TabTitle):
      t.set_class(t.pane_id == self.active, "-active")

  @on(TabPane.Focused)
  def _on_tab_pane_focused(self, event: TabPane.Focused) -> None:
    if event.tab_pane.parent is not self._switcher:
      return
    event.stop()
    tid = event.tab_pane.id
    if tid:
      self.active = tid

  @on(TabTitle.CloseRequested)
  async def _on_title_close(self, event: TabTitle.CloseRequested) -> None:
    await self.remove_pane(event.pane_id)
