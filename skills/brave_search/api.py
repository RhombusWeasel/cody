"""Brave Web Search: vault credential, config default, and HTTP fetch (skill-local)."""

from __future__ import annotations

import logging
from typing import Any

import requests

from utils.cfg_man import cfg, register_default_config

logger = logging.getLogger(__name__)

BRAVE_SEARCH_VAULT_CREDENTIAL_ID = "cody_skill_brave_search_api_key"
BRAVE_SEARCH_VAULT_LABEL = "Brave Search API"
BRAVE_SEARCH_ENV_TOKEN = "BRAVE_SEARCH_API_TOKEN"
BRAVE_WEB_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"
BRAVE_MAX_COUNT = 20

register_default_config({"brave_search": {"max_results": 10}})


def get_brave_api_key() -> str:
  """Return subscription token from vault when unlocked; otherwise empty."""
  try:
    import utils.password_vault as password_vault
  except Exception:
    return ""
  return password_vault.get_secret(BRAVE_SEARCH_VAULT_CREDENTIAL_ID)


def ensure_brave_search_credential_row() -> None:
  """Create empty vault row with human label when missing (OpenAI-style placeholder)."""
  try:
    import utils.password_vault as password_vault
  except Exception:
    return
  if not password_vault.is_unlocked():
    return
  if password_vault.get_credential_by_id(BRAVE_SEARCH_VAULT_CREDENTIAL_ID) is not None:
    return
  password_vault.upsert_credential(
    BRAVE_SEARCH_VAULT_CREDENTIAL_ID,
    BRAVE_SEARCH_VAULT_LABEL,
    "default",
    "",
    "",
  )


def effective_search_limit(override: int | None) -> int:
  if override is not None:
    n = int(override)
  else:
    raw = cfg.get("brave_search.max_results")
    n = int(raw) if raw is not None else 10
  return max(1, min(n, BRAVE_MAX_COUNT))


def fetch_brave_web_search(
  query: str,
  limit: int | None = None,
  api_token: str | None = None,
) -> list[dict[str, Any]]:
  """
  Query Brave Web Search. Pass api_token for subprocess use; otherwise uses vault when unlocked.
  Returns a list of dicts with keys title, url, description (strings).
  """
  q = (query or "").strip()
  if not q:
    raise ValueError("Search query is empty")

  token = (api_token or "").strip() or get_brave_api_key()
  if not token:
    raise ValueError(
      "Brave Search API token missing. Unlock the vault and set the key (Brave sidebar or Vault tab)."
    )

  count = effective_search_limit(limit)
  try:
    resp = requests.get(
      BRAVE_WEB_SEARCH_URL,
      params={"q": q, "count": count},
      headers={
        "Accept": "application/json",
        "X-Subscription-Token": token,
      },
      timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
  except requests.RequestException as e:
    logger.warning("Brave Search request failed: %s", e)
    raise

  web = data.get("web") or {}
  raw_results = web.get("results") or []
  out: list[dict[str, Any]] = []
  for item in raw_results:
    if not isinstance(item, dict):
      continue
    title = item.get("title") or ""
    url = item.get("url") or ""
    desc = item.get("description") or ""
    if url:
      out.append({"title": str(title), "url": str(url), "description": str(desc)})
  return out
