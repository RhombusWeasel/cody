"""TUI flow: unlock vault, ensure OpenAI API key row, prompt if blank; in-process cache for OpenAIProvider."""
from __future__ import annotations

import asyncio

import utils.password_vault as password_vault
from utils.cfg_man import cfg

OPENAI_VAULT_CREDENTIAL_ID = "cody_provider_openai_api_key"
OPENAI_VAULT_LABEL = "OpenAI API key"
OPENAI_VAULT_GROUP = "providers"
OPENAI_VAULT_USERNAME = ""

# Template / example values (e.g. config.json_example) must not skip the vault + key modal.
_PLACEHOLDER_SUBSTRINGS = (
  "nice-try-byok",
  "byok-im-afraid",
  "your-api-key-here",
  "your_api_key_here",
  "changeme",
  "example-api-key",
)

_SESSION_API_KEY: str | None = None


def looks_like_placeholder_openai_api_key(key: str) -> bool:
  k = (key or "").strip()
  if not k:
    return True
  lower = k.lower()
  return any(s in lower for s in _PLACEHOLDER_SUBSTRINGS)


def get_cached_openai_api_key() -> str | None:
  return _SESSION_API_KEY


def set_cached_openai_api_key(key: str | None) -> None:
  global _SESSION_API_KEY
  _SESSION_API_KEY = key.strip() if key else None


def clear_openai_api_key_cache() -> None:
  global _SESSION_API_KEY
  _SESSION_API_KEY = None


def _ensure_credential_row() -> None:
  if password_vault.get_credential_by_id(OPENAI_VAULT_CREDENTIAL_ID) is None:
    password_vault.upsert_credential(
      OPENAI_VAULT_CREDENTIAL_ID,
      OPENAI_VAULT_LABEL,
      OPENAI_VAULT_GROUP,
      OPENAI_VAULT_USERNAME,
      "",
    )


async def _await_modal(app, push_fn) -> bool | str | None:
  loop = asyncio.get_running_loop()
  fut: asyncio.Future = loop.create_future()

  def on_done(result):
    if not fut.done():
      loop.call_soon_threadsafe(fut.set_result, result)

  def push():
    push_fn(on_done)

  app.call_later(push)
  return await fut


async def ensure_openai_api_key_for_tui(app) -> bool:
  """Unlock vault if needed, ensure credential row, prompt for key if empty. Sets session cache on success."""
  if get_cached_openai_api_key():
    return True

  cfg_key = (cfg.get("providers.openai.api_key") or "").strip()
  if cfg_key and not looks_like_placeholder_openai_api_key(cfg_key):
    set_cached_openai_api_key(cfg_key)
    return True

  if not password_vault.is_unlocked():

    def push_unlock(cb):
      password_vault.prompt_master_password(app, on_done=cb)

    unlocked = await _await_modal(app, push_unlock)
    if not unlocked:
      app.notify("Vault unlock cancelled.", severity="warning")
      return False

  _ensure_credential_row()
  row = password_vault.get_credential_by_id(OPENAI_VAULT_CREDENTIAL_ID)
  key = password_vault.decrypt_password(row) if row else ""
  key = (key or "").strip()
  if key:
    set_cached_openai_api_key(key)
    return True

  from components.utils.input_modal import InputModal

  title = (
    "Enter OpenAI API key\n\n"
    "Stored encrypted in your password vault. You can also add it under Vault later."
  )

  def push_key_modal(cb):
    app.push_screen(InputModal(title, password=True), cb)

  entered = await _await_modal(app, push_key_modal)
  if entered is None:
    app.notify("OpenAI API key entry cancelled.", severity="warning")
    return False
  entered = (entered or "").strip()
  if not entered:
    app.notify("OpenAI API key cannot be empty.", severity="error")
    return False

  password_vault.upsert_credential(
    OPENAI_VAULT_CREDENTIAL_ID,
    OPENAI_VAULT_LABEL,
    OPENAI_VAULT_GROUP,
    OPENAI_VAULT_USERNAME,
    entered,
  )
  set_cached_openai_api_key(entered)
  return True
