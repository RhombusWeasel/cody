"""Tab strip container: styled Horizontal holding TabTitle widgets."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal


class TabHeader(Horizontal):
  """Horizontal tab strip; TabContainer mounts TabTitle children here."""

  DEFAULT_CSS = """
  TabHeader {
    height: auto;
    width: 1fr;
    min-width: 0;
  }
  """

  def compose(self) -> ComposeResult:
    yield from ()
