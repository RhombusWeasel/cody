import asyncio
import json
import os
import shutil

from utils.cfg_man import cfg, project_db_base_path
from utils.providers.base import ToolCall
from utils.db_auth import resolve_connection_auth
from utils.db_providers import normalize_conn_type, open_backend


class DatabaseManager:
  def __init__(self):
    self.connections: dict = {}
    self.conn_meta: dict[str, dict] = {}
    self.load_connections()
    self._init_project_db()

  def get_project_db_path(self):
    return project_db_base_path()

  def _is_project_db(self, path: str) -> bool:
    return os.path.abspath(path) == os.path.abspath(project_db_base_path())

  def _init_project_db(self):
    from utils.paths import get_cody_dir
    root_dir = get_cody_dir()
    agents_dir = os.path.join(root_dir, ".agents")
    os.makedirs(agents_dir, exist_ok=True)

    old_db = os.path.join(root_dir, ".cody", "data.db")
    db_path = self.get_project_db_path()
    if os.path.exists(old_db) and not os.path.exists(db_path):
      shutil.copy2(old_db, db_path)

    db_path = self.get_project_db_path()
    self.add_connection(db_path, conn_type="sqlite3", save=True)
    meta = self.conn_meta.get(db_path, {})
    if not meta.get("label"):
      self.conn_meta[db_path] = {**meta, "label": "Cody Data"}
      self._save_connections()

    stmts = [
      '''
            CREATE TABLE IF NOT EXISTS chats (
                id TEXT PRIMARY KEY,
                title TEXT,
                chat_data TEXT,
                working_directory TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''',
      '''
            CREATE TABLE IF NOT EXISTS input_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_input TEXT
            )
        ''',
      '''
            CREATE TABLE IF NOT EXISTS agents (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE,
                description TEXT,
                system_prompt TEXT,
                tool_groups TEXT,
                provider TEXT,
                model TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''',
      '''
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                label TEXT,
                scope TEXT,
                todo_text TEXT,
                creation_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deadline TIMESTAMP,
                status TEXT DEFAULT 'pending',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completion_note TEXT,
                completion_date TIMESTAMP,
                comments TEXT DEFAULT '[]'
            )
        ''',
    ]

    backend = self.connections[db_path]
    for stmt in stmts:
      backend.execute_sync(stmt.strip(), ())

  def load_connections(self):
    saved_connections = cfg.get("db.connections", [])
    needs_save = False
    if isinstance(saved_connections, str):
      try:
        import ast
        saved_connections = ast.literal_eval(saved_connections)
        needs_save = True
      except Exception:
        saved_connections = []
    if not isinstance(saved_connections, list):
      saved_connections = []
      needs_save = True

    from utils.paths import get_cody_dir
    root_dir = get_cody_dir()
    old_db_path = os.path.join(root_dir, ".cody", "data.db")
    new_db_path = self.get_project_db_path()

    for conn_data in saved_connections:
      if isinstance(conn_data, str):
        path = conn_data
        label = None
        conn_type = "sqlite3"
        opts = {}
        auth = {}
        needs_save = True
      elif isinstance(conn_data, dict):
        path = conn_data.get("path")
        label = conn_data.get("label") or None
        conn_type = conn_data.get("type", "sqlite3")
        raw_opts = conn_data.get("opts")
        opts = raw_opts if isinstance(raw_opts, dict) else {}
        raw_auth = conn_data.get("auth")
        auth = raw_auth if isinstance(raw_auth, dict) else {}
      else:
        continue

      if path == old_db_path:
        path = new_db_path
        needs_save = True

      if path:
        try:
          self.add_connection(
            path,
            label=label,
            conn_type=conn_type,
            save=False,
            opts=opts,
            auth=auth,
          )
        except Exception as e:
          print(f"Failed to load database connection {path}: {e}")

    if needs_save:
      self._save_connections()

  def add_connection(
    self,
    path: str,
    label: str | None = None,
    conn_type: str = "sqlite3",
    save: bool = True,
    opts: dict | None = None,
    auth: dict | None = None,
  ):
    if path not in self.connections:
      user_opts = dict(opts or {})
      user_auth = dict(auth) if isinstance(auth, dict) else {}
      resolved = resolve_connection_auth(user_auth)
      normalized_type = normalize_conn_type(conn_type)
      if self._is_project_db(path) and normalized_type == "sqlite3":
        from utils.db_providers.sqlite_encrypted import EncryptedSqliteBackend

        try:
          backend = EncryptedSqliteBackend(path)
        except ValueError as e:
          print(f"Failed to open encrypted Cody database: {e}")
          raise
      else:
        backend = open_backend(
          conn_type, path, user_opts, auth_resolved=resolved
        )
      self.connections[path] = backend
      self.conn_meta[path] = {
        "label": label or "",
        "type": normalized_type,
        "opts": user_opts,
        "auth": user_auth,
      }
      if save:
        self._save_connections()

  def get_label(self, path: str) -> str:
    meta = self.conn_meta.get(path, {})
    return meta.get("label") or os.path.basename(path)

  def remove_connection(self, path: str):
    if path in self.connections:
      self.connections[path].close()
      del self.connections[path]
      self.conn_meta.pop(path, None)
      self._save_connections()

  def _save_connections(self):
    connections_data = []
    for path in self.connections.keys():
      meta = self.conn_meta.get(path, {})
      entry = {"path": path, "type": meta.get("type", "sqlite3")}
      if meta.get("label"):
        entry["label"] = meta["label"]
      opts = meta.get("opts") or {}
      if opts:
        entry["opts"] = opts
      auth = meta.get("auth") or {}
      if auth:
        entry["auth"] = auth
      connections_data.append(entry)
    cfg.set("db.connections", connections_data)

  async def execute(self, path: str, query: str, params: tuple = ()):
    if path not in self.connections:
      raise ValueError(f"No connection found for {path}")
    backend = self.connections[path]
    return await backend.execute(query, params)

  async def list_schema_objects(self, path: str, category: str) -> list[str]:
    if path not in self.connections:
      return []
    return await self.connections[path].list_schema_objects(category)

  def execute_sync(self, path: str, query: str, params: tuple = ()) -> tuple[list[str], list[tuple]]:
    if path not in self.connections:
      raise ValueError(f"No connection found for {path}")
    return self.connections[path].execute_sync(query, params)

  def _serialize_chat_msg(self, msg):
    """Convert a message to JSON-serializable form (handles ToolCall, Function, etc)."""
    if not isinstance(msg, dict):
      return msg
    out = {}
    for k, v in msg.items():
      out[k] = self._serialize_value(v)
    return out

  def _serialize_value(self, v):
    if v is None or isinstance(v, (str, int, float, bool)):
      return v
    if isinstance(v, ToolCall):
      args = v.function.arguments
      if isinstance(args, str):
        try:
          arg_obj = json.loads(args) if args.strip() else {}
        except json.JSONDecodeError:
          arg_obj = {}
      elif isinstance(args, dict):
        arg_obj = args
      else:
        arg_obj = {}
      return {
        "id": v.id or "",
        "type": "function",
        "function": {"name": v.function.name, "arguments": arg_obj},
      }
    if isinstance(v, dict):
      return {k: self._serialize_value(vv) for k, vv in v.items()}
    if isinstance(v, list):
      return [self._serialize_value(item) for item in v]
    if hasattr(v, "model_dump"):
      return self._serialize_value(v.model_dump())
    if hasattr(v, "__dict__"):
      return self._serialize_value(vars(v))
    return str(v)

  async def save_chat(self, chat_id: str, title: str, chat_data: list):
    import json
    serialized = [self._serialize_chat_msg(m) for m in chat_data]
    db_path = self.get_project_db_path()
    working_directory = cfg.get("session.working_directory")
    query = '''
            INSERT INTO chats (id, title, chat_data, working_directory, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                title=excluded.title,
                chat_data=excluded.chat_data,
                working_directory=excluded.working_directory,
                updated_at=CURRENT_TIMESTAMP
        '''
    await self.execute(db_path, query, (chat_id, title, json.dumps(serialized), working_directory))

  async def get_chats(self):
    db_path = self.get_project_db_path()
    working_directory = cfg.get("session.working_directory")
    query = "SELECT id, title, updated_at FROM chats WHERE working_directory = ? ORDER BY updated_at DESC"
    columns, rows = await self.execute(db_path, query, (working_directory,))
    return [{"id": row[0], "title": row[1], "updated_at": row[2]} for row in rows]

  async def get_chat(self, chat_id: str):
    import json
    db_path = self.get_project_db_path()
    query = "SELECT chat_data FROM chats WHERE id = ?"
    columns, rows = await self.execute(db_path, query, (chat_id,))
    if rows:
      return json.loads(rows[0][0])
    return None

  async def delete_chat(self, chat_id: str):
    db_path = self.get_project_db_path()
    query = "DELETE FROM chats WHERE id = ?"
    await self.execute(db_path, query, (str(chat_id),))

  async def get_agents(self):
    db_path = self.get_project_db_path()
    query = "SELECT id, name, description, tool_groups, provider, model, updated_at FROM agents ORDER BY name"
    columns, rows = await self.execute(db_path, query)
    return [
      {
        "id": r[0],
        "name": r[1],
        "description": r[2],
        "tool_groups": r[3],
        "provider": r[4],
        "model": r[5],
        "updated_at": r[6],
      }
      for r in rows
    ]

  async def get_agent_by_name(self, name: str):
    db_path = self.get_project_db_path()
    query = "SELECT id, name, description, system_prompt, tool_groups, provider, model FROM agents WHERE name = ?"
    columns, rows = await self.execute(db_path, query, (name,))
    if rows:
      r = rows[0]
      return {
        "id": r[0],
        "name": r[1],
        "description": r[2],
        "system_prompt": r[3],
        "tool_groups": r[4],
        "provider": r[5],
        "model": r[6],
      }
    return None

  async def get_agent_by_name_or_id(self, id_or_name: str):
    db_path = self.get_project_db_path()
    query = (
      "SELECT id, name, description, system_prompt, tool_groups, provider, model "
      "FROM agents WHERE id = ? OR name = ?"
    )
    columns, rows = await self.execute(db_path, query, (id_or_name, id_or_name))
    if rows:
      r = rows[0]
      return {
        "id": r[0],
        "name": r[1],
        "description": r[2],
        "system_prompt": r[3],
        "tool_groups": r[4],
        "provider": r[5],
        "model": r[6],
      }
    return None

  async def save_agent(
    self,
    agent_id: str,
    name: str,
    description: str,
    system_prompt: str,
    tool_groups: str,
    provider: str,
    model: str,
  ):
    db_path = self.get_project_db_path()
    query = '''
            INSERT INTO agents (id, name, description, system_prompt, tool_groups, provider, model, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                description=excluded.description,
                system_prompt=excluded.system_prompt,
                tool_groups=excluded.tool_groups,
                provider=excluded.provider,
                model=excluded.model,
                updated_at=CURRENT_TIMESTAMP
        '''
    await self.execute(
      db_path,
      query,
      (agent_id, name, description, system_prompt, tool_groups, provider, model),
    )

  async def delete_agent(self, agent_id: str):
    db_path = self.get_project_db_path()
    query = "DELETE FROM agents WHERE id = ?"
    await self.execute(db_path, query, (str(agent_id),))


_db_manager_singleton: DatabaseManager | None = None


def get_db_manager() -> DatabaseManager:
  global _db_manager_singleton
  if _db_manager_singleton is None:
    from utils.cfg_man import ensure_config_loaded_if_needed

    ensure_config_loaded_if_needed()
    _db_manager_singleton = DatabaseManager()
  return _db_manager_singleton


class _DbManagerProxy:
  def __getattr__(self, name: str):
    return getattr(get_db_manager(), name)


db_manager = _DbManagerProxy()
