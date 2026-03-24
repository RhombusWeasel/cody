"""Shared validation for agent tools that fetch from user-supplied http(s) URLs."""

import ipaddress
from urllib.parse import urlparse


def validate_public_http_url(url: str) -> tuple[bool, str]:
  parsed = urlparse(url.strip())
  if parsed.scheme not in ("http", "https"):
    return False, "Only http and https URLs are allowed."
  host = parsed.hostname
  if not host:
    return False, "URL has no host."
  lowered = host.lower()
  if lowered == "localhost" or lowered.endswith(".localhost"):
    return False, "Local hosts are not allowed."
  try:
    ip = ipaddress.ip_address(host)
    if not ip.is_global:
      return False, "Non-public IP addresses are not allowed."
  except ValueError:
    pass
  return True, ""
