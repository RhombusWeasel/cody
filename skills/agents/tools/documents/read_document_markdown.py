import os
from urllib.parse import urlparse

from utils.cfg_man import cfg
from utils.docling_convert import document_source_to_markdown
from utils.safe_url import validate_public_http_url
from utils.tool import register_tool


def read_document_markdown(source: str, max_chars: int = 80000):
  """
  Converts a document (PDF, Office, HTML, images, etc.) to markdown using Docling.

  Use for local project files or public URLs to document binaries—not a substitute for
  fetch_web_page_text on ordinary HTML article pages.

  Args:
    source: Path relative to the session working directory, an absolute path still under
      that directory, or a public http(s) URL to a document.
    max_chars: Maximum characters of markdown to return (longer documents are truncated).

  Returns:
    Markdown prefixed with the source line, suitable for summarization.
  """
  raw = source.strip()
  parsed = urlparse(raw)
  if parsed.netloc and parsed.scheme not in ("http", "https"):
    return "Error: use an explicit https:// URL or a file path, not a scheme-relative URL."

  if parsed.scheme in ("http", "https"):
    ok, err = validate_public_http_url(raw)
    if not ok:
      return f"Error: {err}"
    resolved = raw
  elif parsed.scheme == "file":
    return "Error: file:// URLs are not supported; use a path relative to the working directory."
  else:
    wd = cfg.get("session.working_directory", os.getcwd())
    path = raw if os.path.isabs(raw) else os.path.normpath(os.path.join(wd, raw))
    real_wd = os.path.realpath(wd)
    real_path = os.path.realpath(path)
    try:
      common = os.path.commonpath([real_wd, real_path])
    except ValueError:
      return "Error: path must be under the working directory."
    if common != real_wd:
      return "Error: path must be under the working directory."
    if not os.path.isfile(real_path):
      return f"Error: not a file: {source}"
    resolved = real_path

  body = document_source_to_markdown(resolved, max_chars=max_chars)
  if body.startswith("Error:"):
    return body
  header = f"Source: {source}\n\n"
  return header + body


register_tool("read_document_markdown", read_document_markdown, tags=["documents"])
