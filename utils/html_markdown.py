"""HTML string to Markdown via html-to-markdown (shared by web tools and agents)."""

from html_to_markdown import ConversionOptions, convert


def html_to_markdown(html: str, max_chars: int | None = None) -> str:
  """
  Convert HTML to markdown. On conversion failure returns a string starting with "Error: ".

  Args:
    html: Raw HTML document or fragment.
    max_chars: If set, truncate longer output with a notice suffix.

  Returns:
    Markdown text, or "Error: ..." on failure.
  """
  try:
    opts = ConversionOptions(heading_style="atx")
    text = (convert(html, opts) or "").strip()
  except Exception as e:
    return f"Error: {e}"

  if not text:
    text = "(No text could be extracted from the response.)"

  if max_chars is not None and len(text) > max_chars:
    text = text[:max_chars] + f"\n\n[Truncated at {max_chars} characters]"
  return text
