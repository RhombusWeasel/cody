import asyncio
import os
import sqlite3

from utils.cfg_man import cfg
from utils.config_crypto import decrypt_json_bytes, encrypt_json_bytes


class EncryptedSqliteBackend:
  """
  Cody project SQLite DB held in memory; on disk as Fernet ciphertext (same format as config).
  Reuses salt/iterations from the encrypted config envelope when available.
  """

  def __init__(self, db_base_path: str):
    self._dsn = db_base_path
    self._enc = db_base_path + ".enc"
    self._plain = db_base_path
    self._persist_salt: bytes | None = None
    self._persist_iterations: int | None = None
    self._conn: sqlite3.Connection | None = None
    self._open()

  def _password(self) -> str:
    if not cfg._session_password:
      cfg._ensure_session_password()
    p = cfg._session_password
    if not p:
      raise ValueError(
        "Config password required for encrypted Cody database "
        "(set CODY_CONFIG_PASSWORD or use --config-password-file)."
      )
    return p

  def _persist_to_disk(self) -> None:
    if self._conn is None:
      return
    pwd = self._password()
    if self._persist_salt is None or self._persist_iterations is None:
      self._persist_salt, self._persist_iterations = cfg.kdf_params_for_db_encrypt()
    raw = self._conn.serialize()
    blob = encrypt_json_bytes(
      raw,
      pwd,
      salt=self._persist_salt,
      iterations=self._persist_iterations,
    )
    d = os.path.dirname(self._enc)
    if d:
      os.makedirs(d, exist_ok=True)
    tmp = self._enc + ".tmp"
    with open(tmp, "wb") as f:
      f.write(blob)
    os.replace(tmp, self._enc)

  def _open(self) -> None:
    has_enc = os.path.isfile(self._enc)
    has_plain = os.path.isfile(self._plain)
    if has_enc and has_plain:
      raise ValueError(
        f"Remove either plaintext or encrypted DB: {self._plain} vs {self._enc}"
      )
    if self._conn is not None:
      self._conn.close()
    if has_enc:
      pwd = self._password()
      with open(self._enc, "rb") as f:
        blob = f.read()
      raw, salt, iterations = decrypt_json_bytes(blob, pwd)
      self._persist_salt = salt
      self._persist_iterations = iterations
      self._conn = sqlite3.connect(":memory:", check_same_thread=False, isolation_level=None)
      self._conn.deserialize(raw)
    elif has_plain:
      _ = self._password()
      with open(self._plain, "rb") as f:
        raw = f.read()
      self._conn = sqlite3.connect(":memory:", check_same_thread=False, isolation_level=None)
      self._conn.deserialize(raw)
      self._persist_salt, self._persist_iterations = cfg.kdf_params_for_db_encrypt()
      self._persist_to_disk()
      os.remove(self._plain)
    else:
      self._conn = sqlite3.connect(":memory:", check_same_thread=False, isolation_level=None)

  async def execute(self, query: str, params: tuple = ()) -> tuple[list[str], list[tuple]]:
    conn = self._conn
    if conn is None:
      raise RuntimeError("database connection is closed")

    def _exec():
      cursor = conn.cursor()
      cursor.execute(query, params)
      rows = cursor.fetchall()
      columns = (
        [description[0] for description in cursor.description]
        if cursor.description
        else []
      )
      return columns, rows

    result = await asyncio.to_thread(_exec)
    await asyncio.to_thread(self._persist_to_disk)
    return result

  def execute_sync(self, query: str, params: tuple = ()) -> tuple[list[str], list[tuple]]:
    if self._conn is None:
      raise RuntimeError("database connection is closed")
    conn = self._conn
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    columns = (
      [description[0] for description in cursor.description]
      if cursor.description
      else []
    )
    self._persist_to_disk()
    return columns, rows

  def close(self) -> None:
    try:
      self._persist_to_disk()
    except Exception:
      pass
    if self._conn is not None:
      self._conn.close()
      self._conn = None

  async def list_schema_objects(self, category: str) -> list[str]:
    conn = self._conn
    if conn is None:
      return []
    q = (
      "SELECT name FROM sqlite_master WHERE type = ? AND name NOT LIKE 'sqlite_%' "
      "ORDER BY name"
    )

    def _list():
      cur = conn.cursor()
      cur.execute(q, (category,))
      return [row[0] for row in cur.fetchall()]

    return await asyncio.to_thread(_list)
