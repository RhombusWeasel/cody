"""TUI flow for Ollama Cloud (ollama.com): vault row, session cache; helpers for cloud host detection."""
from __future__ import annotations

import asyncio
import os
from urllib.parse import urlparse

import utils.password_vault as password_vault
from utils.cfg_man import cfg
from utils.providers.openai_vault import looks_like_placeholder_openai_api_key

OLLAMA_VAULT_CREDENTIAL_ID = "cody_provider_ollama_api_key"
OLLAMA_VAULT_LABEL = "Ollama API Key"
OLLAMA_VAULT_GROUP = "providers"
OLLAMA_VAULT_USERNAME = ""

_SESSION_API_KEY: str | None = None


def ollama_base_url_is_cloud(raw: str | None) -> bool:
  s = (raw or "").strip()
  if not s:
    return False
  if "://" not in s:
    s = f"http://{s}"
  host = (urlparse(s).hostname or "").lower()
  return host == "ollama.com" or host.endswith(".ollama.com")


def get_cached_ollama_api_key() -> str | None:
  return _SESSION_API_KEY


def set_cached_ollama_api_key(key: str | None) -> None:
  global _SESSION_API_KEY
  _SESSION_API_KEY = key.strip() if key else None


def clear_ollama_api_key_cache() -> None:
  global _SESSION_API_KEY
  _SESSION_API_KEY = None


def resolve_ollama_api_key() -> str | None:
  """Session cache, then config, vault (if unlocked), then OLLAMA_API_KEY."""
  # Only use API key if connecting to ollama.com cloud
  base = cfg.get("providers.ollama.base_url") or ""
  if not ollama_base_url_is_cloud(base):
    return None
  
  cached = get_cached_ollama_api_key()
  if cached and not looks_like_placeholder_openai_api_key(cached):
    return cached
  cfg_key = (cfg.get("providers.ollama.api_key") or "").strip()
  if cfg_key and not looks_like_placeholder_openai_api_key(cfg_key):
    return cfg_key
  vault_key = password_vault.get_secret(OLLAMA_VAULT_CREDENTIAL_ID)
  if vault_key and not looks_like_placeholder_openai_api_key(vault_key):
    return vault_key
  env_key = (os.getenv("OLLAMA_API_KEY") or "").strip()
  if env_key:
    return env_key
  return None


def _ensure_credential_row() -> None:
  if password_vault.get_credential_by_id(OLLAMA_VAULT_CREDENTIAL_ID) is None:
    password_vault.upsert_credential(
      OLLAMA_VAULT_CREDENTIAL_ID,
      OLLAMA_VAULT_LABEL,
      OLLAMA_VAULT_GROUP,
      OLLAMA_VAULT_USERNAME,
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


async def ensure_ollama_api_key_for_tui(app) -> bool:
  """When base_url targets Ollama Cloud, ensure an API key (vault/modal). No-op for local hosts."""
  base = cfg.get("providers.ollama.base_url") or ""
  if not ollama_base_url_is_cloud(base):
    return True

  cached = get_cached_ollama_api_key()
  if cached and not looks_like_placeholder_openai_api_key(cached):
    return True

  cfg_key = (cfg.get("providers.ollama.api_key") or "").strip()
  if cfg_key and not looks_like_placeholder_openai_api_key(cfg_key):
    set_cached_ollama_api_key(cfg_key)
    return True

  env_key = (os.getenv("OLLAMA_API_KEY") or "").strip()
  if env_key:
    return True

  unlocked = await password_vault._await_unlock()
  if not unlocked:
    app.notify("Vault unlock cancelled.", severity="warning")
    return False

  _ensure_credential_row()
  cred = await password_vault.get_credential(OLLAMA_VAULT_CREDENTIAL_ID)
  key = cred.get("password") or ""
  if key:
    set_cached_ollama_api_key(key)
    return True

  from components.utils.input_modal import InputModal

  title = (
    "Enter Ollama API key\n\n"
    "Stored encrypted in your password vault. You can also add it under Vault later "
    "(providers / Ollama API Key), set providers.ollama.api_key, or set OLLAMA_API_KEY."
  )

  def push_key_modal(cb):
    app.push_screen(InputModal(title, password=True), cb)

  entered = await _await_modal(app, push_key_modal)
  if entered is None:
    app.notify("Ollama API key entry cancelled.", severity="warning")
    return False
  entered = (entered or "").strip()
  if not entered:
    app.notify("Ollama API key cannot be empty.", severity="error")
    return False

  password_vault.register_credential(
    OLLAMA_VAULT_CREDENTIAL_ID,
    OLLAMA_VAULT_GROUP,
    OLLAMA_VAULT_USERNAME,
    entered,
  )
  set_cached_ollama_api_key(entered)
  return True
