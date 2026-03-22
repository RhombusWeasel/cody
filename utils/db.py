import sqlite3
import asyncio
import json
import os
import shutil
from utils.cfg_man import cfg

class DatabaseManager:
    def __init__(self):
        self.connections = {}
        self.conn_meta: dict[str, dict] = {}
        self.load_connections()
        self._init_project_db()

    def get_project_db_path(self):
        from utils.paths import get_cody_dir
        agents_dir = os.path.join(get_cody_dir(), ".agents")
        return os.path.join(agents_dir, "cody_data.db")

    def _init_project_db(self):
        from utils.paths import get_cody_dir
        root_dir = get_cody_dir()
        agents_dir = os.path.join(root_dir, ".agents")
        os.makedirs(agents_dir, exist_ok=True)

        # One-time migration from .cody/data.db to .agents/cody_data.db
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
        
        # Initialize tables
        conn = self.connections[db_path]
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

    def load_connections(self):
        saved_connections = cfg.get("db.connections", [])
        needs_save = False
        if isinstance(saved_connections, str):
            try:
                import ast
                saved_connections = ast.literal_eval(saved_connections)
                needs_save = True
            except:
                saved_connections = []
        if not isinstance(saved_connections, list):
            saved_connections = []
            needs_save = True
            
        from utils.paths import get_cody_dir
        root_dir = get_cody_dir()
        old_db_path = os.path.join(root_dir, ".cody", "data.db")
        new_db_path = self.get_project_db_path()

        for conn_data in saved_connections:
            # Handle legacy string format
            if isinstance(conn_data, str):
                path = conn_data
                label = None
                conn_type = "sqlite3"
                needs_save = True
            elif isinstance(conn_data, dict):
                path = conn_data.get("path")
                label = conn_data.get("label") or None
                conn_type = conn_data.get("type", "sqlite3")
            else:
                continue

            if path == old_db_path:
                path = new_db_path
                needs_save = True

            if path:
                try:
                    self.add_connection(path, label=label, conn_type=conn_type, save=False)
                except Exception as e:
                    print(f"Failed to load database connection {path}: {e}")
                    
        if needs_save:
            self._save_connections()

    def add_connection(self, path: str, label: str | None = None, conn_type: str = "sqlite3", save: bool = True):
        if path not in self.connections:
            self.connections[path] = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
            self.conn_meta[path] = {"label": label or "", "type": conn_type}
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
            connections_data.append(entry)
        cfg.set("db.connections", connections_data)

    async def execute(self, path: str, query: str, params: tuple = ()):
        if path not in self.connections:
            raise ValueError(f"No connection found for {path}")
        
        conn = self.connections[path]
        
        def _exec():
            cursor = conn.cursor()
            cursor.execute(query, params)
            # conn.commit() is no longer needed since isolation_level=None enables autocommit
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description] if cursor.description else []
            return columns, rows
            
        return await asyncio.to_thread(_exec)

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
        import json
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
        import json
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

db_manager = DatabaseManager()
