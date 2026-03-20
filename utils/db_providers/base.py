from typing import Protocol


class DbBackend(Protocol):
  """Pluggable database connection: execute queries and optional schema introspection.

  Backend ``opts`` may include auth-related keys (username, password, token, sslmode,
  sslrootcert, sslcert, sslkey) after resolution from db.connections[].auth.
  """

  async def execute(self, query: str, params: tuple = ()) -> tuple[list[str], list[tuple]]:
    """Run a query; return (column_names, rows)."""
    ...

  def execute_sync(self, query: str, params: tuple = ()) -> tuple[list[str], list[tuple]]:
    """Same as execute but blocking; safe under a running asyncio loop."""
    ...

  def close(self) -> None:
    ...

  async def list_schema_objects(self, category: str) -> list[str]:
    """List object names for category: table, view, trigger (backend-specific)."""
    ...
