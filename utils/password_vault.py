"""Encrypted password vault: ~/.agents/cody_passwords_db.enc (JSON with encrypted secret fields).

**Public API** (extensions and skills): ``init_vault``, ``register_credential``,
``register_secure_note``, ``get_credential``, ``get_secure_note``. Other names in this
module are for Cody core (sidebar, providers) only.
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
import uuid
from pathlib import Path
from typing import Any, Callable

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

__all__ = [
  "init_vault",
  "register_credential",
  "register_secure_note",
  "get_credential",
  "get_secure_note",
]

VAULT_VERSION = 1
KDF_ITERATIONS = 480_000
SESSION_KEY: bytes | None = None
_DATA: dict[str, Any] | None = None
_vault_session_clear_hooks: list[Callable[[], None]] = []
_tui_app: Any | None = None
# Concurrent prompt_master_password callers share one InputModal; callbacks run when it completes.
_unlock_waiters: list[Callable[[bool], None]] = []

_CRED = "credentials"
_NOTE = "notes"


def init_vault(app: Any | None) -> None:
  """Register the running Textual app (TUI); ``None`` on shutdown or non-TUI contexts."""
  global _tui_app
  _tui_app = app


def get_app() -> Any | None:
  return _tui_app


def vault_path() -> Path:
  return Path.home() / ".agents" / "cody_passwords_db.enc"


def is_file_present() -> bool:
  return vault_path().is_file()


def is_unlocked() -> bool:
  return SESSION_KEY is not None and _DATA is not None


def register_vault_session_clear_hook(fn: Callable[[], None]) -> None:
  """Extensions (e.g. bundled skills) run ``fn`` when the vault session is cleared (lock)."""
  if fn not in _vault_session_clear_hooks:
    _vault_session_clear_hooks.append(fn)


def clear_session_key() -> None:
  global SESSION_KEY, _DATA
  SESSION_KEY = None
  _DATA = None
  try:
    from utils.providers.openai_vault import clear_openai_api_key_cache
    clear_openai_api_key_cache()
  except ImportError:
    pass
  try:
    from utils.providers.ollama_vault import clear_ollama_api_key_cache
    clear_ollama_api_key_cache()
  except ImportError:
    pass
  for hook in _vault_session_clear_hooks:
    try:
      hook()
    except Exception:
      pass


def _derive_fernet_key(password: str, salt: bytes) -> bytes:
  kdf = PBKDF2HMAC(
    algorithm=hashes.SHA256(),
    length=32,
    salt=salt,
    iterations=KDF_ITERATIONS,
  )
  raw = kdf.derive(password.encode("utf-8"))
  return base64.urlsafe_b64encode(raw)


def _fernet() -> Fernet:
  if SESSION_KEY is None:
    raise RuntimeError("Vault is locked")
  return Fernet(SESSION_KEY)


def _encrypt_field(plain: str) -> str:
  return _fernet().encrypt(plain.encode("utf-8")).decode("ascii")


def _decrypt_field(token: str) -> str:
  return _fernet().decrypt(token.encode("ascii")).decode("utf-8")


def _default_data(salt_b64: str) -> dict[str, Any]:
  return {"version": VAULT_VERSION, "kdf_salt": salt_b64, _CRED: [], _NOTE: []}


def _validate_decryption(data: dict[str, Any]) -> bool:
  f = _fernet()
  for coll, cipher_key in ((_CRED, "password_cipher"), (_NOTE, "body_cipher")):
    for row in data.get(coll, []):
      tok = row.get(cipher_key) or ""
      if tok:
        try:
          f.decrypt(tok.encode("ascii"))
        except InvalidToken:
          return False
  return True


def try_unlock(password: str) -> bool:
  """Unlock vault or create new vault file. Returns False if wrong password for existing file."""
  global SESSION_KEY, _DATA
  path = vault_path()
  path.parent.mkdir(parents=True, exist_ok=True)

  if not path.is_file():
    salt = os.urandom(16)
    salt_b64 = base64.standard_b64encode(salt).decode("ascii")
    SESSION_KEY = _derive_fernet_key(password, salt)
    _DATA = _default_data(salt_b64)
    _save_raw()
    return True

  try:
    raw = json.loads(path.read_text(encoding="utf-8"))
  except (json.JSONDecodeError, OSError):
    return False

  salt_b64 = raw.get("kdf_salt")
  if not salt_b64 or raw.get("version") != VAULT_VERSION:
    return False
  try:
    salt = base64.standard_b64decode(salt_b64.encode("ascii"))
  except (ValueError, TypeError):
    return False

  SESSION_KEY = _derive_fernet_key(password, salt)
  if not _validate_decryption(raw):
    SESSION_KEY = None
    _DATA = None
    return False

  _DATA = {
    "version": VAULT_VERSION,
    "kdf_salt": salt_b64,
    _CRED: list(raw.get(_CRED, [])),
    _NOTE: list(raw.get(_NOTE, [])),
  }
  return True


def _save_raw() -> None:
  if _DATA is None:
    raise RuntimeError("Vault is locked")
  path = vault_path()
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(json.dumps(_DATA, indent=2), encoding="utf-8")


def _require_data() -> dict[str, Any]:
  if _DATA is None:
    raise RuntimeError("Vault is locked")
  return _DATA


def _snapshot(collection: str) -> list[dict[str, Any]]:
  if _DATA is None:
    return []
  return [dict(x) for x in _DATA.get(collection, [])]


def _entry_snapshot(collection: str, entry_id: str) -> dict[str, Any] | None:
  if _DATA is None:
    return None
  for row in _DATA.get(collection, []):
    if row.get("id") == entry_id:
      return dict(row)
  return None


def _upsert_secret_row(
  collection: str,
  entry_id: str | None,
  label: str,
  group: str,
  plain_secret: str,
  *,
  username: str | None,
) -> None:
  rows: list[dict[str, Any]] = _require_data()[collection]
  cipher = _encrypt_field(plain_secret)
  g = group or "default"

  def row_dict(rid: str) -> dict[str, Any]:
    base = {"id": rid, "label": label, "group": g}
    if username is not None:
      base["username"] = username
      base["password_cipher"] = cipher
    else:
      base["body_cipher"] = cipher
    return base

  if entry_id:
    for i, row in enumerate(rows):
      if row.get("id") == entry_id:
        rows[i] = row_dict(entry_id)
        _save_raw()
        return
  new_id = entry_id or str(uuid.uuid4())
  rows.append(row_dict(new_id))
  _save_raw()


def upsert_credential(
  entry_id: str | None,
  label: str,
  group: str,
  username: str,
  password_plain: str,
) -> None:
  _upsert_secret_row(_CRED, entry_id, label, group, password_plain, username=username)


def upsert_note(
  entry_id: str | None,
  label: str,
  group: str,
  body_plain: str,
) -> None:
  _upsert_secret_row(_NOTE, entry_id, label, group, body_plain, username=None)


def _delete_by_id(collection: str, entry_id: str) -> None:
  d = _require_data()
  d[collection] = [x for x in d[collection] if x.get("id") != entry_id]
  _save_raw()


def delete_credential(entry_id: str) -> None:
  _delete_by_id(_CRED, entry_id)


def delete_note(entry_id: str) -> None:
  _delete_by_id(_NOTE, entry_id)


def list_credentials() -> list[dict[str, Any]]:
  return _snapshot(_CRED)


def list_notes() -> list[dict[str, Any]]:
  return _snapshot(_NOTE)


def get_credential_by_id(entry_id: str) -> dict[str, Any] | None:
  return _entry_snapshot(_CRED, entry_id)


def get_note_by_id(entry_id: str) -> dict[str, Any] | None:
  return _entry_snapshot(_NOTE, entry_id)


def _decrypt_cipher_cell(row: dict[str, Any], cipher_key: str) -> str:
  tok = row.get(cipher_key) or ""
  if not tok:
    return ""
  return _decrypt_field(tok)


def decrypt_password(row: dict[str, Any]) -> str:
  return _decrypt_cipher_cell(row, "password_cipher")


def decrypt_note_body(row: dict[str, Any]) -> str:
  return _decrypt_cipher_cell(row, "body_cipher")


def register_credential(
  credential_name: str,
  group: str,
  default_username: str,
  default_password: str,
) -> None:
  """Upsert a credential; ``credential_name`` is the stable row id. Preserves ``label`` on update."""
  existing = _entry_snapshot(_CRED, credential_name)
  label = (existing.get("label") if existing else None) or credential_name
  upsert_credential(credential_name, label, group, default_username, default_password)


def register_secure_note(secure_note_name: str, group: str, data: str) -> None:
  """Upsert a secure note; ``secure_note_name`` is the stable row id. Preserves ``label`` on update."""
  existing = _entry_snapshot(_NOTE, secure_note_name)
  label = (existing.get("label") if existing else None) or secure_note_name
  upsert_note(secure_note_name, label, group, data)


def _read_credential_plain(entry_id: str) -> dict[str, str]:
  row = _entry_snapshot(_CRED, entry_id)
  if not row:
    return {"username": "", "password": ""}
  try:
    pwd = (_decrypt_cipher_cell(row, "password_cipher") or "").strip()
    user = (row.get("username") or "").strip()
    return {"username": user, "password": pwd}
  except (InvalidToken, ValueError, TypeError):
    return {"username": "", "password": ""}


def _read_note_plain(entry_id: str) -> str:
  row = _entry_snapshot(_NOTE, entry_id)
  if not row:
    return ""
  try:
    return (_decrypt_cipher_cell(row, "body_cipher") or "").strip()
  except (InvalidToken, ValueError, TypeError):
    return ""


def get_secret(entry_id: str) -> str:
  """Decrypted password for credential ``entry_id`` when already unlocked; else ``\"\"``."""
  if not is_unlocked():
    return ""
  return _read_credential_plain(entry_id)["password"]


def get_credential_username(entry_id: str) -> str:
  """Username when unlocked; else ``\"\"``."""
  if not is_unlocked():
    return ""
  return _read_credential_plain(entry_id)["username"]


async def _await_unlock() -> bool:
  if is_unlocked():
    return True
  app = get_app()
  if app is None:
    return False
  loop = asyncio.get_running_loop()
  fut: asyncio.Future[bool] = loop.create_future()

  def on_done(ok: bool) -> None:
    if not fut.done():
      loop.call_soon_threadsafe(fut.set_result, ok)

  def push() -> None:
    prompt_master_password(app=app, on_done=on_done)

  app.call_later(push)
  return await fut


async def get_credential(credential_name: str) -> dict[str, str]:
  """Return ``username`` and ``password`` for ``credential_name`` (row id). Awaits unlock modal if needed."""
  if not is_unlocked() and not await _await_unlock():
    return {"username": "", "password": ""}
  return _read_credential_plain(credential_name)


async def get_secure_note(secure_note_name: str) -> str:
  """Decrypted note body for ``secure_note_name`` (row id). Awaits unlock modal if needed."""
  if not is_unlocked() and not await _await_unlock():
    return ""
  return _read_note_plain(secure_note_name)


def _flush_unlock_waiters(ok: bool) -> None:
  global _unlock_waiters
  waiters = list(_unlock_waiters)
  _unlock_waiters.clear()
  for cb in waiters:
    try:
      cb(ok)
    except Exception:
      pass


def prompt_master_password(
  app=None,
  *,
  on_done: Callable[[bool], None],
  create_mode: bool | None = None,
) -> None:
  """Show InputModal if needed; cache session key on success. Calls on_done(True) when unlocked."""
  from components.utils.input_modal import InputModal

  if is_unlocked():
    on_done(True)
    return

  app = app or get_app()
  if app is None:
    on_done(False)
    return

  _unlock_waiters.append(on_done)
  if len(_unlock_waiters) > 1:
    return

  creating = create_mode if create_mode is not None else not is_file_present()
  title = "Create master password" if creating else "Unlock password vault"

  def on_modal_result(pw: str | None) -> None:
    if pw is None:
      _flush_unlock_waiters(False)
      return
    if not pw:
      app.notify("Password cannot be empty.", severity="error")
      _flush_unlock_waiters(False)
      return
    if try_unlock(pw):
      _flush_unlock_waiters(True)
    else:
      app.notify("Wrong password or corrupted vault.", severity="error")
      _flush_unlock_waiters(False)

  app.push_screen(InputModal(title, password=True), on_modal_result)
