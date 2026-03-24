"""Form schema and save helpers for DB sidebar / settings connections."""
from __future__ import annotations

import uuid
from typing import Any

from utils.password_vault import is_unlocked, register_credential, register_secure_note

COSMOS_AUTH_OPTIONS = [
  "default_azure",
  "connection_string",
  "account_key",
  "client_secret",
  "managed_identity",
  "resource_tokens",
]

CONN_TYPE_OPTIONS = ["sqlite3", "cosmos"]

VAULT_GROUP = "cosmos_db"


def connection_form_schema(args: dict | None) -> list[dict[str, Any]]:
  """Fields for SQLite and Cosmos; visibility by ``type`` and Cosmos ``auth_kind``; finalize enforces both."""
  _ = args
  sw_sqlite = {"key": "type", "value": "sqlite3"}
  sw_cosmos = {"key": "type", "value": "cosmos"}
  sw_auth_conn_str = {"key": "auth_kind", "value": "connection_string"}
  sw_auth_rsrc_tok = {"key": "auth_kind", "value": "resource_tokens"}
  sw_auth_acct_key = {"key": "auth_kind", "value": "account_key"}
  sw_auth_sp = {"key": "auth_kind", "value": "client_secret"}
  sw_auth_mi = {"key": "auth_kind", "value": "managed_identity"}
  sw_note_auths = {"key": "auth_kind", "values": ["connection_string", "resource_tokens"]}
  sw_cred_auths = {"key": "auth_kind", "values": ["account_key", "client_secret"]}
  return [
    {"key": "label", "label": "Label", "type": "text", "placeholder": "e.g. Production"},
    {
      "key": "type",
      "label": "Type",
      "type": "select",
      "options": CONN_TYPE_OPTIONS,
      "required": True,
    },
    {
      "key": "path",
      "label": "SQLite database path",
      "type": "text",
      "placeholder": "/path/to/db.sqlite",
      "show_when": sw_sqlite,
    },
    {"key": "endpoint", "label": "Cosmos account endpoint (URL)", "type": "text", "show_when": sw_cosmos},
    {"key": "database", "label": "Cosmos database name", "type": "text", "show_when": sw_cosmos},
    {"key": "container", "label": "Cosmos default container", "type": "text", "show_when": sw_cosmos},
    {
      "key": "auth_kind",
      "label": "Cosmos authentication",
      "type": "select",
      "options": COSMOS_AUTH_OPTIONS,
      "show_when": sw_cosmos,
    },
    {
      "key": "vault_note_id",
      "label": "Vault secure note id (optional if pasting below)",
      "type": "text",
      "show_when_all": [sw_cosmos, sw_note_auths],
    },
    {
      "key": "vault_cred_id",
      "label": "Vault credential id (optional if pasting below)",
      "type": "text",
      "show_when_all": [sw_cosmos, sw_cred_auths],
    },
    {
      "key": "tenant_id",
      "label": "Cosmos tenant id (client_secret auth)",
      "type": "text",
      "show_when_all": [sw_cosmos, sw_auth_sp],
    },
    {
      "key": "managed_identity_client_id",
      "label": "User-assigned managed identity client id (optional)",
      "type": "text",
      "show_when_all": [sw_cosmos, sw_auth_mi],
    },
    {
      "key": "inline_connection_string",
      "label": "Paste Cosmos connection string once (vault note)",
      "type": "textarea",
      "show_when_all": [sw_cosmos, sw_auth_conn_str],
    },
    {
      "key": "inline_account_key",
      "label": "Paste Cosmos account key once (vault credential)",
      "type": "password",
      "show_when_all": [sw_cosmos, sw_auth_acct_key],
    },
    {
      "key": "inline_resource_tokens_json",
      "label": "Paste resource tokens JSON once (vault note)",
      "type": "textarea",
      "show_when_all": [sw_cosmos, sw_auth_rsrc_tok],
    },
    {
      "key": "inline_sp_client_id",
      "label": "Paste Entra app (client) id once",
      "type": "text",
      "show_when_all": [sw_cosmos, sw_auth_sp],
    },
    {
      "key": "inline_sp_client_secret",
      "label": "Paste client secret once (vault credential)",
      "type": "password",
      "show_when_all": [sw_cosmos, sw_auth_sp],
    },
  ]


def finalize_connection_dict(result: dict[str, Any], app: Any) -> dict[str, Any] | None:
  ctype = (result.get("type") or "sqlite3").strip() or "sqlite3"
  out: dict[str, Any] = {"type": ctype}

  label = (result.get("label") or "").strip()
  if label:
    out["label"] = label

  if ctype == "sqlite3":
    path = (result.get("path") or "").strip()
    if not path:
      app.notify("Database path is required for SQLite.", severity="error")
      return None
    out["path"] = path
    out["id"] = (result.get("id") or "").strip() or path
    return out

  def require_vault() -> bool:
    if not is_unlocked():
      app.notify("Unlock the password vault first (sidebar lock icon).", severity="error")
      return False
    return True

  auth = (result.get("auth_kind") or "default_azure").strip()
  endpoint = (result.get("endpoint") or "").strip()
  database = (result.get("database") or "").strip()
  container = (result.get("container") or "").strip()
  if not endpoint or not database or not container:
    app.notify("Cosmos requires endpoint, database, and default container.", severity="error")
    return None

  out["id"] = (result.get("id") or "").strip() or f"cosmos_{uuid.uuid4().hex}"
  out["endpoint"] = endpoint
  out["database"] = database
  out["container"] = container
  out["auth_kind"] = auth

  tenant = (result.get("tenant_id") or "").strip()
  if tenant:
    out["tenant_id"] = tenant
  mic = (result.get("managed_identity_client_id") or "").strip()
  if mic:
    out["managed_identity_client_id"] = mic

  note_id_in = (result.get("vault_note_id") or "").strip()
  cred_id_in = (result.get("vault_cred_id") or "").strip()

  inline_cs = (result.get("inline_connection_string") or "").strip()
  inline_key = (result.get("inline_account_key") or "").strip()
  inline_tok = (result.get("inline_resource_tokens_json") or "").strip()
  sp_id = (result.get("inline_sp_client_id") or "").strip()
  sp_secret = (result.get("inline_sp_client_secret") or "").strip()

  if auth == "connection_string":
    if inline_cs:
      if not require_vault():
        return None
      nid = f"cosmos_conn_str_{uuid.uuid4().hex[:12]}"
      register_secure_note(nid, VAULT_GROUP, inline_cs)
      out["vault_note_id"] = nid
    elif note_id_in:
      out["vault_note_id"] = note_id_in
    else:
      app.notify("Provide a vault note id or paste a connection string.", severity="error")
      return None

  elif auth == "resource_tokens":
    if inline_tok:
      if not require_vault():
        return None
      nid = f"cosmos_rsrc_tok_{uuid.uuid4().hex[:12]}"
      register_secure_note(nid, VAULT_GROUP, inline_tok)
      out["vault_note_id"] = nid
    elif note_id_in:
      out["vault_note_id"] = note_id_in
    else:
      app.notify("Provide a vault note id or paste resource tokens JSON.", severity="error")
      return None

  elif auth == "account_key":
    if inline_key:
      if not require_vault():
        return None
      cid = f"cosmos_acct_key_{uuid.uuid4().hex[:12]}"
      register_credential(cid, VAULT_GROUP, "", inline_key)
      out["vault_cred_id"] = cid
    elif cred_id_in:
      out["vault_cred_id"] = cred_id_in
    else:
      app.notify("Provide a vault credential id or paste the account key.", severity="error")
      return None

  elif auth == "client_secret":
    if not tenant:
      app.notify("Tenant id is required for client_secret auth.", severity="error")
      return None
    if sp_id and sp_secret:
      if not require_vault():
        return None
      cid = f"cosmos_sp_{uuid.uuid4().hex[:12]}"
      register_credential(cid, VAULT_GROUP, sp_id, sp_secret)
      out["vault_cred_id"] = cid
    elif cred_id_in:
      out["vault_cred_id"] = cred_id_in
    else:
      app.notify("Provide a vault credential id or paste app id and client secret.", severity="error")
      return None

  elif auth in ("default_azure", "managed_identity"):
    pass
  else:
    app.notify(f"Unknown auth kind: {auth}", severity="error")
    return None

  return out
