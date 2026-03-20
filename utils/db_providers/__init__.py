from utils.db_providers.base import DbBackend
from utils.db_providers.sqlite import SqliteBackend

BACKENDS: dict[str, type] = {
  "sqlite3": SqliteBackend,
}


def normalize_conn_type(conn_type: str) -> str:
  t = (conn_type or "sqlite3").strip().lower()
  if t in ("sqlite", "sqlite3"):
    return "sqlite3"
  return t


def open_backend(
  conn_type: str,
  dsn: str,
  opts: dict | None = None,
  auth_resolved: dict | None = None,
) -> DbBackend:
  key = normalize_conn_type(conn_type)
  cls = BACKENDS.get(key)
  if cls is None:
    raise ValueError(
      f"Unknown database type {conn_type!r}. Supported: {', '.join(sorted(BACKENDS))}"
    )
  merged = dict(opts or {})
  if auth_resolved:
    merged.update(auth_resolved)
  return cls(dsn, merged)
