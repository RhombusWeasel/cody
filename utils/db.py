import asyncio
import json
import os
import shutil
import uuid

from utils.cfg_man import cfg, register_default_config
from utils.db_providers import CosmosDbProvider, SqliteDbProvider
from utils.password_vault import register_vault_session_clear_hook

register_default_config({"db": {"connections": []}})


class DatabaseManager:
  def __init__(self):
    self.connections: dict[str, SqliteDbProvider | CosmosDbProvider] = {}
    self.conn_meta: dict[str, dict] = {}
    register_vault_session_clear_hook(self._on_vault_clear)
    self.load_connections()
    self._init_project_db()

  def _on_vault_clear(self) -> None:
    for prov in self.connections.values():
      if isinstance(prov, CosmosDbProvider):
        prov.clear_client()

  def get_project_db_path(self):
    from utils.paths import get_cody_dir
    agents_dir = os.path.join(get_cody_dir(), ".agents")
    return os.path.join(agents_dir, "cody_data.db")

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
    self._open_sqlite(db_path, label="Cody Data", save=True)
    meta = self.conn_meta.get(db_path, {})
    if not meta.get("label"):
      self.conn_meta[db_path] = {**meta, "label": "Cody Data"}
      self._save_connections()

    prov = self.connections[db_path]
    conn = prov.sqlite_connection
    cursor = conn.cursor()
    cursor.execute('''
            CREATE TABLE IF NOT EXISTS chats (
                id TEXT PRIMARY KEY,
                title TEXT,
                chat_data TEXT,
                working_directory TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    cursor.execute('''
            CREATE TABLE IF NOT EXISTS input_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_input TEXT
            )
        ''')
    cursor.execute('''
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
        ''')
    cursor.execute('''
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                label TEXT,
                scope TEXT,
                todo_text TEXT,
                creation_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deadline TIMESTAMP,
                status TEXT DEFAULT 'pending',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    self._seed_bundled_agents(cursor)

  def _seed_bundled_agents(self, cursor):
    from utils.paths import bundled_agent_definitions_dir

    bund = bundled_agent_definitions_dir()
    if not os.path.isdir(bund):
      return
    for entry in sorted(os.listdir(bund)):
      if not entry.endswith(".json"):
        continue
      path = os.path.join(bund, entry)
      try:
        with open(path, encoding="utf-8") as f:
          data = json.load(f)
      except (OSError, json.JSONDecodeError):
        continue
      name = data.get("name")
      if not name:
        continue
      cursor.execute("SELECT 1 FROM agents WHERE name = ?", (name,))
      if cursor.fetchone():
        continue
      agent_id = data.get("id") or name
      desc = data.get("description") or ""
      prompt = data.get("system_prompt") or ""
      groups = data.get("tool_groups") or []
      tool_groups = json.dumps(groups)
      provider = data.get("provider") or ""
      model = data.get("model") or ""
      cursor.execute(
        """
                INSERT INTO agents (id, name, description, system_prompt, tool_groups, provider, model, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
        (agent_id, name, desc, prompt, tool_groups, provider, model),
      )

  def _normalize_saved_item(self, conn_data: dict | str, old_db_path: str, new_db_path: str) -> dict | None:
    if isinstance(conn_data, str):
      return {"path": conn_data, "type": "sqlite3", "id": conn_data}
    if not isinstance(conn_data, dict):
      return None
    path = conn_data.get("path")
    if path == old_db_path:
      conn_data = {**conn_data, "path": new_db_path, "id": conn_data.get("id", new_db_path)}
    return conn_data

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

    for raw in saved_connections:
      conn_data = self._normalize_saved_item(raw, old_db_path, new_db_path)
      if conn_data is None:
        continue
      if isinstance(raw, str):
        needs_save = True
      if conn_data.get("type", "sqlite3") == "cosmos" and not (conn_data.get("id") or "").strip():
        conn_data = {**conn_data, "id": f"cosmos_{uuid.uuid4().hex}"}
        needs_save = True
      try:
        self._open_connection_dict(conn_data, save=False)
      except Exception as e:
        print(f"Failed to load database connection: {e}")

    if needs_save:
      self._save_connections()

  def reload_from_config(self) -> None:
    """Drop non-project connections and reopen from ``cfg`` (after settings edit)."""
    proj = self.get_project_db_path()
    for cid in list(self.connections.keys()):
      if cid == proj:
        continue
      self.connections[cid].close()
      del self.connections[cid]
      self.conn_meta.pop(cid, None)

    saved_connections = cfg.get("db.connections", [])
    if not isinstance(saved_connections, list):
      return
    from utils.paths import get_cody_dir
    old_db_path = os.path.join(get_cody_dir(), ".cody", "data.db")
    new_db_path = self.get_project_db_path()
    for raw in saved_connections:
      conn_data = self._normalize_saved_item(raw, old_db_path, new_db_path)
      if conn_data is None:
        continue
      try:
        self._open_connection_dict(conn_data, save=False)
      except Exception as e:
        print(f"Failed to load database connection: {e}")

  def _open_connection_dict(self, conn_data: dict, save: bool) -> None:
    conn_type = (conn_data.get("type") or "sqlite3").strip()
    if conn_type == "cosmos":
      cid = (conn_data.get("id") or "").strip() or f"cosmos_{uuid.uuid4().hex}"
      meta = {**conn_data, "id": cid, "type": "cosmos"}
      if cid in self.connections:
        self.connections[cid].close()
      self.connections[cid] = CosmosDbProvider(cid, meta)
      self.conn_meta[cid] = meta
      if save:
        self._save_connections()
      return

    path = (conn_data.get("path") or "").strip()
    if not path:
      return
    label = conn_data.get("label") or None
    self._open_sqlite(path, label=label, save=save)

  def _open_sqlite(self, path: str, label: str | None, save: bool) -> None:
    if path in self.connections:
      existing = self.connections[path]
      if not isinstance(existing, SqliteDbProvider):
        existing.close()
        del self.connections[path]
      else:
        meta = self.conn_meta.get(path, {})
        self.conn_meta[path] = {
          **meta,
          "label": label if label is not None else meta.get("label", ""),
          "type": "sqlite3",
          "path": path,
        }
        if save:
          self._save_connections()
        return
    self.connections[path] = SqliteDbProvider(path)
    self.conn_meta[path] = {"label": label or "", "type": "sqlite3", "path": path}
    if save:
      self._save_connections()

  def add_connection(
    self,
    path: str | None = None,
    label: str | None = None,
    conn_type: str = "sqlite3",
    save: bool = True,
    connection_dict: dict | None = None,
  ) -> None:
    if connection_dict is not None:
      self._open_connection_dict(connection_dict, save=save)
      return
    if conn_type == "cosmos":
      raise ValueError("Use connection_dict= for Cosmos connections.")
    if not path:
      raise ValueError("path is required for SQLite connections.")
    self._open_sqlite(path, label=label, save=save)

  def get_explorer_categories(self, conn_id: str) -> list[str]:
    meta = self.conn_meta.get(conn_id, {})
    if meta.get("type") == "cosmos":
      return ["container"]
    return ["table", "view", "trigger"]

  def get_label(self, conn_id: str) -> str:
    meta = self.conn_meta.get(conn_id, {})
    if meta.get("type") == "cosmos":
      return meta.get("label") or meta.get("id") or conn_id
    return meta.get("label") or os.path.basename(meta.get("path", conn_id))

  def remove_connection(self, conn_id: str, save: bool = True) -> None:
    proj = self.get_project_db_path()
    if conn_id == proj:
      return
    if conn_id in self.connections:
      self.connections[conn_id].close()
      del self.connections[conn_id]
      self.conn_meta.pop(conn_id, None)
      if save:
        self._save_connections()

  def update_saved_connection(self, old_conn_id: str, connection_dict: dict) -> str | None:
    """Replace one entry in ``db.connections`` and reload. Returns new id, or ``None`` if blocked / missing."""
    proj = self.get_project_db_path()
    if old_conn_id == proj:
      return None
    lst = cfg.get("db.connections", [])
    if not isinstance(lst, list):
      return None
    idx = None
    for i, raw in enumerate(lst):
      if isinstance(raw, str):
        rid = raw.strip()
      elif isinstance(raw, dict):
        rid = str(raw.get("id") or raw.get("path") or "").strip()
      else:
        continue
      if rid == old_conn_id:
        idx = i
        break
    if idx is None:
      return None
    new_lst = list(lst)
    new_lst[idx] = connection_dict
    cfg.set("db.connections", new_lst)
    cfg.changed = False
    self.reload_from_config()
    return str(connection_dict.get("id") or connection_dict.get("path") or old_conn_id)

  def _serialize_connection_entry(self, conn_id: str) -> dict:
    meta = dict(self.conn_meta.get(conn_id, {}))
    ctype = meta.get("type", "sqlite3")
    entry: dict = {"id": conn_id, "type": ctype}
    if meta.get("label"):
      entry["label"] = meta["label"]
    if ctype == "sqlite3":
      entry["path"] = meta.get("path", conn_id)
      return entry
    for k in (
      "endpoint",
      "database",
      "container",
      "auth_kind",
      "vault_note_id",
      "vault_cred_id",
      "tenant_id",
      "managed_identity_client_id",
    ):
      v = meta.get(k)
      if v:
        entry[k] = v
    return entry

  def _save_connections(self):
    connections_data = [self._serialize_connection_entry(cid) for cid in self.connections.keys()]
    cfg.set("db.connections", connections_data)

  async def execute(self, conn_id: str, query: str, params: tuple = ()):
    if conn_id not in self.connections:
      raise ValueError(f"No connection found for {conn_id}")
    prov = self.connections[conn_id]
    return await prov.execute(query, params)

  async def list_sidebar_children(self, conn_id: str, category: str) -> list[str]:
    if conn_id not in self.connections:
      return []
    return await self.connections[conn_id].list_sidebar_children(category)

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
    serialized = [self._serialize_chat_msg(m) for m in chat_data]
    db_path = self.get_project_db_path()
    working_directory = cfg.get('session.working_directory')
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
    working_directory = cfg.get('session.working_directory')
    query = 'SELECT id, title, updated_at FROM chats WHERE working_directory = ? ORDER BY updated_at DESC'
    columns, rows = await self.execute(db_path, query, (working_directory,))
    return [{"id": row[0], "title": row[1], "updated_at": row[2]} for row in rows]

  async def get_chat(self, chat_id: str):
    db_path = self.get_project_db_path()
    query = 'SELECT chat_data FROM chats WHERE id = ?'
    columns, rows = await self.execute(db_path, query, (chat_id,))
    if rows:
      return json.loads(rows[0][0])
    return None

  async def delete_chat(self, chat_id: str):
    db_path = self.get_project_db_path()
    query = 'DELETE FROM chats WHERE id = ?'
    await self.execute(db_path, query, (str(chat_id),))

  async def get_agents(self):
    db_path = self.get_project_db_path()
    query = 'SELECT id, name, description, tool_groups, provider, model, updated_at FROM agents ORDER BY name'
    columns, rows = await self.execute(db_path, query)
    return [
      {"id": r[0], "name": r[1], "description": r[2],
       "tool_groups": r[3], "provider": r[4], "model": r[5], "updated_at": r[6]}
      for r in rows
    ]

  async def get_agent_by_name(self, name: str):
    db_path = self.get_project_db_path()
    query = 'SELECT id, name, description, system_prompt, tool_groups, provider, model FROM agents WHERE name = ?'
    columns, rows = await self.execute(db_path, query, (name,))
    if rows:
      r = rows[0]
      return {"id": r[0], "name": r[1], "description": r[2],
              "system_prompt": r[3], "tool_groups": r[4], "provider": r[5], "model": r[6]}
    return None

  async def get_agent_by_name_or_id(self, id_or_name: str):
    db_path = self.get_project_db_path()
    query = 'SELECT id, name, description, system_prompt, tool_groups, provider, model FROM agents WHERE id = ? OR name = ?'
    columns, rows = await self.execute(db_path, query, (id_or_name, id_or_name))
    if rows:
      r = rows[0]
      return {"id": r[0], "name": r[1], "description": r[2],
              "system_prompt": r[3], "tool_groups": r[4], "provider": r[5], "model": r[6]}
    return None

  async def save_agent(self, agent_id: str, name: str, description: str,
                       system_prompt: str, tool_groups: str, provider: str, model: str):
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
    await self.execute(db_path, query, (agent_id, name, description, system_prompt, tool_groups, provider, model))

  async def delete_agent(self, agent_id: str):
    db_path = self.get_project_db_path()
    query = 'DELETE FROM agents WHERE id = ?'
    await self.execute(db_path, query, (str(agent_id),))


_db_manager_instance = None


def _get_db_manager():
  global _db_manager_instance
  if _db_manager_instance is None:
    _db_manager_instance = DatabaseManager()
  return _db_manager_instance


class _DbManagerProxy:
  __slots__ = ()

  def __getattr__(self, name):
    return getattr(_get_db_manager(), name)


db_manager = _DbManagerProxy()
