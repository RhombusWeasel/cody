import asyncio
import sqlite3


class SqliteBackend:
  """SQLite file DSN via sqlite3; async execute uses a worker thread."""

  def __init__(self, dsn: str, opts: dict | None = None):
    self._dsn = dsn
    self._opts = opts or {}
    self._conn = sqlite3.connect(dsn, check_same_thread=False, isolation_level=None)

  async def execute(self, query: str, params: tuple = ()) -> tuple[list[str], list[tuple]]:
    conn = self._conn

    def _exec():
      cursor = conn.cursor()
      cursor.execute(query, params)
      rows = cursor.fetchall()
      columns = [description[0] for description in cursor.description] if cursor.description else []
      return columns, rows

    return await asyncio.to_thread(_exec)

  def execute_sync(self, query: str, params: tuple = ()) -> tuple[list[str], list[tuple]]:
    conn = self._conn
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    columns = (
      [description[0] for description in cursor.description]
      if cursor.description
      else []
    )
    return columns, rows

  def close(self) -> None:
    self._conn.close()

  async def list_schema_objects(self, category: str) -> list[str]:
    conn = self._conn
    q = (
      "SELECT name FROM sqlite_master WHERE type = ? AND name NOT LIKE 'sqlite_%' "
      "ORDER BY name"
    )

    def _list():
      cur = conn.cursor()
      cur.execute(q, (category,))
      return [row[0] for row in cur.fetchall()]

    return await asyncio.to_thread(_list)
