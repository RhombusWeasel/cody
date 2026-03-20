"""Tiered postit JSON load/save and HTTP execution."""
import json
import os
import re

import requests

import utils.fs as fs
from utils.paths import get_tiered_paths

HTTP_METHODS = frozenset(
  ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS")
)

NEW_KEY = "__new__"


def load_merged_requests(working_dir: str) -> dict[str, dict]:
  """Merge JSON stems from tiered postit dirs; later tiers override."""
  merged: dict[str, dict] = {}
  for base in get_tiered_paths("postit", working_dir):
    if os.path.isdir(base):
      merged.update(fs.load_folder(base, ".json"))
  return merged


def stem_source_map(working_dir: str) -> dict[str, str]:
  """Map each stem to the directory path that last defined it."""
  out: dict[str, str] = {}
  for base in get_tiered_paths("postit", working_dir):
    if not os.path.isdir(base):
      continue
    for name in os.listdir(base):
      if not name.endswith(".json"):
        continue
      stem = name[:-5]
      out[stem] = base
  return out


def sanitize_stem(s: str) -> str:
  s = (s or "").strip()
  s = re.sub(r"[^\w\-.]+", "_", s)
  return s or "untitled"


def default_postit_dir(working_dir: str) -> str:
  return os.path.join(working_dir, ".agents", "postit")


def default_save_path(working_dir: str, stem: str) -> str:
  stem = sanitize_stem(stem)
  return os.path.join(default_postit_dir(working_dir), f"{stem}.json")


def normalize_request(raw: dict) -> tuple[dict | None, str | None]:
  if not isinstance(raw, dict):
    return None, "request must be a JSON object"
  method = str(raw.get("method", "GET")).upper()
  if method not in HTTP_METHODS:
    return None, f"invalid method: {method}"
  url = raw.get("url") or ""
  if not isinstance(url, str) or not url.strip():
    return None, "url is required"
  headers = raw.get("headers") or {}
  if not isinstance(headers, dict):
    return None, "headers must be a JSON object"
  h2 = {str(k): str(v) for k, v in headers.items()}
  body = raw.get("body")
  if body is None:
    body = ""
  elif not isinstance(body, str):
    body = json.dumps(body)
  out = {
    "version": int(raw.get("version", 1)),
    "method": method,
    "url": url.strip(),
    "headers": h2,
    "body": body,
  }
  if raw.get("name") is not None:
    out["name"] = raw["name"]
  if raw.get("label") is not None:
    out["label"] = raw["label"]
  return out, None


def request_from_ui_fields(
  method: str,
  url: str,
  headers_text: str,
  body: str,
) -> tuple[dict | None, str | None]:
  try:
    headers_obj = json.loads(headers_text.strip() or "{}")
  except json.JSONDecodeError as e:
    return None, f"headers JSON: {e}"
  if not isinstance(headers_obj, dict):
    return None, "headers must be a JSON object"
  raw = {"method": method, "url": url, "headers": headers_obj, "body": body}
  return normalize_request(raw)


def write_request(working_dir: str, stem: str, data: dict) -> tuple[str | None, str | None]:
  norm, err = normalize_request(data)
  if err:
    return None, err
  stem = sanitize_stem(stem)
  d = default_postit_dir(working_dir)
  os.makedirs(d, exist_ok=True)
  path = os.path.join(d, f"{stem}.json")
  fs.save_data(path, norm)
  return path, None


def execute_request(norm: dict, timeout: float = 30.0) -> requests.Response:
  kwargs: dict = {
    "method": norm["method"],
    "url": norm["url"],
    "headers": norm["headers"],
    "timeout": timeout,
  }
  if norm.get("body"):
    kwargs["data"] = norm["body"]
  return requests.request(**kwargs)
