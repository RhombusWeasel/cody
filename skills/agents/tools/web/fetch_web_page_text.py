import requests

from utils.html_markdown import html_to_markdown
from utils.safe_url import validate_public_http_url
from utils.tool import register_tool


def fetch_web_page_text(url: str, max_chars: int = 80000):
  """
  Fetches a public web page over HTTP(S) and returns the body as Markdown for summarization.
  Args:
    url: Full http or https URL to fetch.
    max_chars: Maximum characters of markdown body to return (longer pages are truncated).
  Returns:
    Markdown body prefixed with the source URL and content type, suitable for summarization.
  """
  ok, err = validate_public_http_url(url)
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

  body = html_to_markdown(raw, max_chars=max_chars)
  if body.startswith("Error:"):
    return body

  header = f"Source: {url}\nContent-Type: {resp.headers.get('Content-Type', 'unknown')}\n\n"
  return header + body


register_tool("fetch_web_page_text", fetch_web_page_text, tags=["web"])
