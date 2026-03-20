"""Resolve per-connection DB auth from config + env into flat opts keys for backends."""
import os

from utils.cfg_man import cfg, expand_config_value


def _resolve_field(
  auth: dict,
  direct_key: str,
  env_key: str,
  cfg_key: str,
) -> str:
  """Order: explicit (with interpolation), env var name, cfg dot path."""
  raw = auth.get(direct_key)
  if raw is not None and str(raw).strip():
    return expand_config_value(str(raw).strip())

  env_name = auth.get(env_key)
  if env_name and str(env_name).strip():
    return os.environ.get(str(env_name).strip(), "")

  cfg_path = auth.get(cfg_key)
  if cfg_path and str(cfg_path).strip():
    path = str(cfg_path).strip()
    v = cfg.get(path, "")
    if v is None or v == "":
      return ""
    return expand_config_value(str(v))

  return ""


def _flatten_ssl(ssl_block: dict | None) -> dict:
  """Map auth.ssl object to driver-oriented keys (Postgres-style names)."""
  if not isinstance(ssl_block, dict):
    return {}
  out = {}
  mode = ssl_block.get("mode")
  if mode is not None and str(mode).strip():
    out["sslmode"] = str(mode).strip()
  for src, dest in (
    ("rootcert", "sslrootcert"),
    ("cert", "sslcert"),
    ("key", "sslkey"),
  ):
    v = ssl_block.get(src)
    if v is not None and str(v).strip():
      out[dest] = expand_config_value(str(v).strip())
  return out


def resolve_connection_auth(auth: dict | None) -> dict:
  """
  Turn db.connections[].auth into flat kwargs merged into backend opts.
  Methods: none, dsn (no merge), password, token.
  """
  if not auth or not isinstance(auth, dict):
    return {}

  method = (auth.get("method") or "none").strip().lower()
  if method in ("none", "dsn"):
    out = {}
    out.update(_flatten_ssl(auth.get("ssl") if isinstance(auth.get("ssl"), dict) else None))
    return out

  out = {}

  if method == "password":
    username = _resolve_field(auth, "username", "username_env", "username_cfg")
    password = _resolve_field(auth, "password", "password_env", "password_cfg")
    if username:
      out["username"] = username
    if password:
      out["password"] = password

  elif method == "token":
    token = _resolve_field(auth, "token", "token_env", "token_cfg")
    if token:
      out["token"] = token

  out.update(_flatten_ssl(auth.get("ssl") if isinstance(auth.get("ssl"), dict) else None))
  return out
