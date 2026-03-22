"""TUI flow: unlock vault, ensure memory service credential row; in-process cache for MemoryClient."""
from __future__ import annotations

import asyncio
import os

import utils.password_vault as password_vault
from utils.cfg_man import cfg

MEMORY_VAULT_CREDENTIAL_ID = "cody_skill_memory_password"
MEMORY_VAULT_LABEL = "Memory service"
MEMORY_VAULT_GROUP = "skills"
MEMORY_VAULT_USERNAME = ""

# (username, password) for Reverie POST /login; None until TUI ensure or first resolve.
_SESSION_CREDS: tuple[str, str] | None = None


def get_cached_memory_credentials() -> tuple[str, str] | None:
  return _SESSION_CREDS


def set_cached_memory_credentials(username: str, password: str) -> None:
  global _SESSION_CREDS
  _SESSION_CREDS = (username, password)


def clear_memory_password_cache() -> None:
  global _SESSION_CREDS
  _SESSION_CREDS = None


def _ensure_credential_row() -> None:
  if password_vault.get_credential_by_id(MEMORY_VAULT_CREDENTIAL_ID) is None:
    password_vault.upsert_credential(
      MEMORY_VAULT_CREDENTIAL_ID,
      MEMORY_VAULT_LABEL,
      MEMORY_VAULT_GROUP,
      MEMORY_VAULT_USERNAME,
      "",
    )


def resolve_memory_credentials() -> tuple[str, str]:
  """Reverie login username and password; prefers vault row when unlocked, then cfg/env."""
  if _SESSION_CREDS is not None:
    return _SESSION_CREDS

  cfg_u = (cfg.get("memory.username") or "").strip()
  cfg_p = (cfg.get("memory.password") or "").strip()
  env_p = (os.environ.get("CODY_MEMORY_PASSWORD") or "").strip()

  if password_vault.is_unlocked():
    _ensure_credential_row()
    row = password_vault.get_credential_by_id(MEMORY_VAULT_CREDENTIAL_ID)
    if row:
      vault_u = (row.get("username") or "").strip()
      vault_p = (password_vault.decrypt_password(row) or "").strip()
      u = vault_u or cfg_u
      p = vault_p or cfg_p or env_p
      return (u, p)

  p = cfg_p or env_p
  return (cfg_u, p)


def resolve_memory_password() -> str:
  return resolve_memory_credentials()[1]


async def _await_modal(app, push_fn):
  loop = asyncio.get_running_loop()
  fut: asyncio.Future = loop.create_future()

  def on_done(result):
    if not fut.done():
      loop.call_soon_threadsafe(fut.set_result, result)

  def push():
    push_fn(on_done)

  app.call_later(push)
  return await fut


async def ensure_memory_password_for_tui(app) -> bool:
  """Unlock vault if needed; fill session creds from vault row, cfg, or env."""
  if _SESSION_CREDS is not None:
    return True

  cfg_p = (cfg.get("memory.password") or "").strip()
  if cfg_p:
    set_cached_memory_credentials(
      (cfg.get("memory.username") or "").strip(),
      cfg_p,
    )
    return True

  env_p = (os.environ.get("CODY_MEMORY_PASSWORD") or "").strip()
  if env_p:
    set_cached_memory_credentials(
      (cfg.get("memory.username") or "").strip(),
      env_p,
    )
    return True

  if not password_vault.is_unlocked():

    def push_unlock(cb):
      password_vault.prompt_master_password(app, on_done=cb)

    unlocked = await _await_modal(app, push_unlock)
    if not unlocked:
      app.notify("Vault unlock cancelled (needed for memory credentials).", severity="warning")
      return False

  _ensure_credential_row()
  row = password_vault.get_credential_by_id(MEMORY_VAULT_CREDENTIAL_ID)
  u, p = (cfg.get("memory.username") or "").strip(), ""
  if row:
    u = ((row.get("username") or "").strip() or u)
    p = (password_vault.decrypt_password(row) or "").strip()

  base = (cfg.get("memory.base_url") or "").strip()
  if base:
    from components.utils.input_modal import InputModal

    need_save = False
    if not u:
      title_u = (
        "Reverie / memory username\n\n"
        "Same as POST /login. Saved on the vault row’s username field."
      )

      def push_u(cb):
        app.push_screen(InputModal(title_u, password=False), cb)

      entered_u = await _await_modal(app, push_u)
      if entered_u is None:
        app.notify("Memory username entry cancelled.", severity="warning")
        return False
      u = (entered_u or "").strip()
      if not u:
        app.notify("Memory username is required when memory.base_url is set.", severity="error")
        return False
      need_save = True

    if not p:
      title_p = (
        "Reverie / memory password\n\n"
        "Account password for POST /login. Stored encrypted in the vault."
      )

      def push_pw_modal(cb):
        app.push_screen(InputModal(title_p, password=True), cb)

      entered = await _await_modal(app, push_pw_modal)
      if entered is None:
        app.notify("Memory password entry cancelled.", severity="warning")
        return False
      p = (entered or "").strip()
      if not p:
        app.notify("Memory password is required when memory.base_url is set.", severity="error")
        return False
      need_save = True

    if need_save:
      password_vault.upsert_credential(
        MEMORY_VAULT_CREDENTIAL_ID,
        MEMORY_VAULT_LABEL,
        MEMORY_VAULT_GROUP,
        u,
        p,
      )

  set_cached_memory_credentials(u, p)
  return True
