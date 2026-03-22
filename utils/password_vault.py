"""Encrypted password vault: ~/.agents/cody_passwords_db.enc (JSON with encrypted secret fields)."""
from __future__ import annotations

import base64
import json
import os
import uuid
from pathlib import Path
from typing import Any, Callable

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

VAULT_VERSION = 1
KDF_ITERATIONS = 480_000
SESSION_KEY: bytes | None = None
_DATA: dict[str, Any] | None = None


def vault_path() -> Path:
  return Path.home() / ".agents" / "cody_passwords_db.enc"


def is_file_present() -> bool:
  return vault_path().is_file()


def is_unlocked() -> bool:
  return SESSION_KEY is not None and _DATA is not None


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
    from utils.memory_vault import clear_memory_password_cache
    clear_memory_password_cache()
  except ImportError:
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
  return {
    "version": VAULT_VERSION,
    "kdf_salt": salt_b64,
    "credentials": [],
    "notes": [],
  }


def _validate_decryption(data: dict[str, Any]) -> bool:
  f = _fernet()
  for c in data.get("credentials", []):
    tok = c.get("password_cipher") or ""
    if tok:
      try:
        f.decrypt(tok.encode("ascii"))
      except InvalidToken:
        return False
  for n in data.get("notes", []):
    tok = n.get("body_cipher") or ""
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
    "credentials": list(raw.get("credentials", [])),
    "notes": list(raw.get("notes", [])),
  }
  return True


def _save_raw() -> None:
  if _DATA is None:
    raise RuntimeError("Vault is locked")
  path = vault_path()
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(json.dumps(_DATA, indent=2), encoding="utf-8")


def save() -> None:
  _save_raw()


def list_credentials() -> list[dict[str, Any]]:
  if _DATA is None:
    return []
  return [dict(x) for x in _DATA.get("credentials", [])]


def list_notes() -> list[dict[str, Any]]:
  if _DATA is None:
    return []
  return [dict(x) for x in _DATA.get("notes", [])]


def decrypt_password(row: dict[str, Any]) -> str:
  tok = row.get("password_cipher") or ""
  if not tok:
    return ""
  return _decrypt_field(tok)


def decrypt_note_body(row: dict[str, Any]) -> str:
  tok = row.get("body_cipher") or ""
  if not tok:
    return ""
  return _decrypt_field(tok)


def upsert_credential(
  entry_id: str | None,
  label: str,
  group: str,
  username: str,
  password_plain: str,
) -> None:
  if _DATA is None:
    raise RuntimeError("Vault is locked")
  creds: list[dict[str, Any]] = _DATA["credentials"]
  cipher = _encrypt_field(password_plain)
  if entry_id:
    for i, c in enumerate(creds):
      if c.get("id") == entry_id:
        creds[i] = {
          "id": entry_id,
          "label": label,
          "group": group or "default",
          "username": username,
          "password_cipher": cipher,
        }
        _save_raw()
        return
  new_id = entry_id or str(uuid.uuid4())
  creds.append({
    "id": new_id,
    "label": label,
    "group": group or "default",
    "username": username,
    "password_cipher": cipher,
  })
  _save_raw()


def upsert_note(
  entry_id: str | None,
  label: str,
  group: str,
  body_plain: str,
) -> None:
  if _DATA is None:
    raise RuntimeError("Vault is locked")
  notes: list[dict[str, Any]] = _DATA["notes"]
  cipher = _encrypt_field(body_plain)
  if entry_id:
    for i, n in enumerate(notes):
      if n.get("id") == entry_id:
        notes[i] = {
          "id": entry_id,
          "label": label,
          "group": group or "default",
          "body_cipher": cipher,
        }
        _save_raw()
        return
  new_id = entry_id or str(uuid.uuid4())
  notes.append({
    "id": new_id,
    "label": label,
    "group": group or "default",
    "body_cipher": cipher,
  })
  _save_raw()


def delete_credential(entry_id: str) -> None:
  if _DATA is None:
    raise RuntimeError("Vault is locked")
  _DATA["credentials"] = [c for c in _DATA["credentials"] if c.get("id") != entry_id]
  _save_raw()


def delete_note(entry_id: str) -> None:
  if _DATA is None:
    raise RuntimeError("Vault is locked")
  _DATA["notes"] = [n for n in _DATA["notes"] if n.get("id") != entry_id]
  _save_raw()


def get_credential_by_id(entry_id: str) -> dict[str, Any] | None:
  for c in list_credentials():
    if c.get("id") == entry_id:
      return c
  return None


def get_note_by_id(entry_id: str) -> dict[str, Any] | None:
  for n in list_notes():
    if n.get("id") == entry_id:
      return n
  return None


def prompt_master_password(
  app,
  *,
  on_done: Callable[[bool], None],
  create_mode: bool | None = None,
) -> None:
  """Show InputModal if needed; cache session key on success. Calls on_done(True) when unlocked."""
  from components.utils.input_modal import InputModal

  if is_unlocked():
    on_done(True)
    return

  creating = create_mode if create_mode is not None else not is_file_present()
  title = "Create master password" if creating else "Unlock password vault"

  def on_modal_result(pw: str | None) -> None:
    if pw is None:
      on_done(False)
      return
    if not pw:
      app.notify("Password cannot be empty.", severity="error")
      on_done(False)
      return
    if try_unlock(pw):
      on_done(True)
    else:
      app.notify("Wrong password or corrupted vault.", severity="error")
      on_done(False)

  app.push_screen(InputModal(title, password=True), on_modal_result)
