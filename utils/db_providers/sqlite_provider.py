"""SQLite file connection for the DB sidebar."""
from __future__ import annotations

import asyncio
import sqlite3
from typing import Any


class SqliteDbProvider:
  def __init__(self, path: str):
    self.path = path
    self._conn = sqlite3.connect(path, check_same_thread=False, isolation_level=None)

  @property
  def db_kind(self) -> str:
    return "sqlite3"

  @property
  def sqlite_connection(self) -> sqlite3.Connection:
    return self._conn

  async def execute(self, query: str, params: tuple[Any, ...] = ()) -> tuple[list[str], list[tuple]]:
    conn = self._conn

    def _exec() -> tuple[list[str], list[tuple]]:
      cursor = conn.cursor()
      cursor.execute(query, params)
      rows = cursor.fetchall()
      columns = [description[0] for description in cursor.description] if cursor.description else []
      return columns, rows

    return await asyncio.to_thread(_exec)

  async def list_sidebar_children(self, category: str) -> list[str]:
    if category not in ("table", "view", "trigger"):
      return []

    def _list() -> list[str]:
      cur = self._conn.cursor()
      cur.execute(
        f"SELECT name FROM sqlite_master WHERE type=? AND name NOT LIKE 'sqlite_%' ORDER BY name;",
        (category,),
      )
      return [r[0] for r in cur.fetchall()]

    return await asyncio.to_thread(_list)

  def close(self) -> None:
    self._conn.close()
