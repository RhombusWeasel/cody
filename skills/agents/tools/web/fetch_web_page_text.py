import html
import ipaddress
import re
from html.parser import HTMLParser
from urllib.parse import urlparse

import requests

from utils.tool import register_tool

_BLOCK_TAGS = frozenset({
  "address", "article", "aside", "blockquote", "br", "caption", "dd", "div", "dt",
  "fieldset", "figcaption", "figure", "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6",
  "header", "hr", "li", "main", "nav", "p", "pre", "section", "table", "tbody", "td",
  "tfoot", "th", "thead", "title", "tr",
})
_SKIP_TAGS = frozenset({"script", "style", "noscript"})


def _strip_script_style(raw: str) -> str:
  out = re.sub(r"<script\b[^>]*>[\s\S]*?</script>", "", raw, flags=re.I)
  out = re.sub(r"<style\b[^>]*>[\s\S]*?</style>", "", out, flags=re.I)
  return out


class _HtmlToText(HTMLParser):
  def __init__(self):
    super().__init__(convert_charrefs=True)
    self._parts: list[str] = []
    self._skip_depth = 0

  def handle_starttag(self, tag, attrs):
    t = tag.lower()
    if t in _SKIP_TAGS:
      self._skip_depth += 1
      return
    if self._skip_depth:
      return
    if t in _BLOCK_TAGS:
      self._parts.append("\n")

  def handle_endtag(self, tag):
    t = tag.lower()
    if t in _SKIP_TAGS and self._skip_depth:
      self._skip_depth -= 1
      return
    if self._skip_depth:
      return
    if t in _BLOCK_TAGS:
      self._parts.append("\n")

  def handle_data(self, data):
    if self._skip_depth:
      return
    if data.strip():
      self._parts.append(data)

  def get_text(self) -> str:
    return html.unescape("".join(self._parts))


def _validate_fetch_url(url: str) -> tuple[bool, str]:
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


def _html_to_text(html_doc: str) -> str:
  cleaned = _strip_script_style(html_doc)
  parser = _HtmlToText()
  parser.feed(cleaned)
  parser.close()
  text = parser.get_text()
  text = re.sub(r"[ \t]+\n", "\n", text)
  text = re.sub(r"\n{3,}", "\n\n", text)
  return text.strip()


def fetch_web_page_text(url: str, max_chars: int = 80000):
  """
  Fetches a public web page over HTTP(S) and returns extracted plain text for summarization.
  Args:
    url: Full http or https URL to fetch.
    max_chars: Maximum characters of extracted text to return (longer pages are truncated).
  Returns:
    Plain text body prefixed with the source URL, suitable for summarizing in markdown.
  """
  ok, err = _validate_fetch_url(url)
  if not ok:
    return f"Error: {err}"

  headers = {
    "User-Agent": "Mozilla/5.0 (compatible; CodyPageSummarizer/1.0; +https://github.com/)",
  }
  try:
    resp = requests.get(
      url,
      headers=headers,
      timeout=30,
      allow_redirects=True,
    )
    resp.raise_for_status()
    raw = resp.text or ""
  except requests.RequestException as e:
    return f"Error fetching URL: {e}"

  text = _html_to_text(raw)
  if not text:
    text = "(No text could be extracted from the response.)"

  header = f"Source: {url}\nContent-Type: {resp.headers.get('Content-Type', 'unknown')}\n\n"
  body = text
  if len(body) > max_chars:
    body = body[:max_chars] + f"\n\n[Truncated at {max_chars} characters]"
  return header + body


register_tool("fetch_web_page_text", fetch_web_page_text, tags=["web"])
