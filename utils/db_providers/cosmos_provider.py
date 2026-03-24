"""Azure Cosmos DB Core (NoSQL) API — sidebar connections only."""
from __future__ import annotations

import asyncio
import json
from typing import Any

from azure.cosmos import CosmosClient
from azure.identity import ClientSecretCredential, DefaultAzureCredential, ManagedIdentityCredential

from utils.password_vault import get_credential, get_secure_note


def _flatten_cell(v: Any) -> Any:
  if v is None or isinstance(v, (str, int, float, bool)):
    return v
  if isinstance(v, (dict, list)):
    return json.dumps(v, default=str)
  return str(v)


def _documents_to_grid(items: list[dict[str, Any]]) -> tuple[list[str], list[tuple]]:
  if not items:
    return [], []
  keys: list[str] = sorted({k for doc in items for k in doc.keys()})
  rows = [tuple(_flatten_cell(doc.get(k)) for k in keys) for doc in items]
  return keys, rows


async def build_cosmos_client(meta: dict[str, Any]) -> CosmosClient:
  auth = (meta.get("auth_kind") or "default_azure").strip()
  if auth == "connection_string":
    note_id = (meta.get("vault_note_id") or "").strip()
    raw = (await get_secure_note(note_id)).strip()
    if not raw:
      raise ValueError("Cosmos connection string missing (vault note empty or vault locked).")
    return CosmosClient.from_connection_string(raw)

  if auth == "account_key":
    endpoint = (meta.get("endpoint") or "").strip()
    if not endpoint:
      raise ValueError("Cosmos endpoint is required.")
    cred_id = (meta.get("vault_cred_id") or "").strip()
    c = await get_credential(cred_id)
    key = (c.get("password") or "").strip()
    if not key:
      raise ValueError("Cosmos account key missing (credential password empty or vault locked).")
    return CosmosClient(endpoint, credential=key)

  if auth == "default_azure":
    endpoint = (meta.get("endpoint") or "").strip()
    if not endpoint:
      raise ValueError("Cosmos endpoint is required.")
    return CosmosClient(endpoint, DefaultAzureCredential())

  if auth == "client_secret":
    endpoint = (meta.get("endpoint") or "").strip()
    tenant = (meta.get("tenant_id") or "").strip()
    cred_id = (meta.get("vault_cred_id") or "").strip()
    if not endpoint or not tenant:
      raise ValueError("Cosmos endpoint and tenant_id are required for client_secret auth.")
    c = await get_credential(cred_id)
    app_id = (c.get("username") or "").strip()
    secret = (c.get("password") or "").strip()
    if not app_id or not secret:
      raise ValueError("App id / secret missing (vault credential empty or vault locked).")
    credential = ClientSecretCredential(tenant, app_id, secret)
    return CosmosClient(endpoint, credential)

  if auth == "managed_identity":
    endpoint = (meta.get("endpoint") or "").strip()
    if not endpoint:
      raise ValueError("Cosmos endpoint is required.")
    mic_id = (meta.get("managed_identity_client_id") or "").strip()
    credential = ManagedIdentityCredential(client_id=mic_id) if mic_id else ManagedIdentityCredential()
    return CosmosClient(endpoint, credential)

  if auth == "resource_tokens":
    endpoint = (meta.get("endpoint") or "").strip()
    note_id = (meta.get("vault_note_id") or "").strip()
    if not endpoint:
      raise ValueError("Cosmos endpoint is required.")
    raw = (await get_secure_note(note_id)).strip()
    if not raw:
      raise ValueError("Resource tokens missing (vault note empty or vault locked).")
    tokens = json.loads(raw)
    if not isinstance(tokens, dict):
      raise ValueError("Resource tokens note must contain a JSON object.")
    return CosmosClient(endpoint, credential=tokens)

  raise ValueError(f"Unknown Cosmos auth_kind: {auth!r}")


class CosmosDbProvider:
  def __init__(self, conn_id: str, meta: dict[str, Any]):
    self.conn_id = conn_id
    self.meta = dict(meta)
    self._client: CosmosClient | None = None

  @property
  def db_kind(self) -> str:
    return "cosmos"

  def clear_client(self) -> None:
    self._client = None

  def close(self) -> None:
    self.clear_client()

  async def _ensure_client(self) -> CosmosClient:
    if self._client is None:
      self._client = await build_cosmos_client(self.meta)
    return self._client

  def _default_container_name(self) -> str:
    return (self.meta.get("container") or "").strip()

  def _database_name(self) -> str:
    return (self.meta.get("database") or "").strip()

  async def execute(self, query: str, params: tuple[Any, ...] = ()) -> tuple[list[str], list[tuple]]:
    if params:
      raise ValueError("Parameterized Cosmos DB sidebar queries are not supported; use literals in SQL.")
    container_name = self._default_container_name()
    if not container_name:
      raise ValueError("Default container name is required for Cosmos queries.")
    db_name = self._database_name()
    if not db_name:
      raise ValueError("Database name is required.")

    client = await self._ensure_client()
    container = client.get_database_client(db_name).get_container_client(container_name)

    def _run_query() -> tuple[list[str], list[tuple]]:
      pager = container.query_items(
        query=query,
        enable_cross_partition_query=True,
      )
      items = list(pager)
      return _documents_to_grid(items)

    return await asyncio.to_thread(_run_query)

  async def list_sidebar_children(self, category: str) -> list[str]:
    if category != "container":
      return []
    db_name = self._database_name()
    if not db_name:
      return []

    client = await self._ensure_client()

    def _list() -> list[str]:
      db = client.get_database_client(db_name)
      return [c["id"] for c in db.list_containers()]

    return sorted(await asyncio.to_thread(_list))
