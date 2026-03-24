"""DB sidebar connection providers (SQLite file, Azure Cosmos Core API)."""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class DbSidebarProvider(Protocol):
  """Async query execution + optional schema explorer for the DB sidebar."""

  @property
  def db_kind(self) -> str:
    """``sqlite3`` or ``cosmos``."""

  async def execute(self, query: str, params: tuple[Any, ...] = ()) -> tuple[list[str], list[tuple]]:
    """Return column names and row tuples (same shape as sqlite cursor)."""

  async def list_sidebar_children(self, category: str) -> list[str]:
    """SQLite: ``table`` / ``view`` / ``trigger``. Cosmos: ``container``."""

  def close(self) -> None:
    """Release native resources."""
