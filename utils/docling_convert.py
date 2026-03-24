"""Convert Docling-supported sources (path or URL) to markdown. No cfg dependency."""

_converter = None


def _get_converter():
  global _converter
  if _converter is None:
    from docling.document_converter import DocumentConverter

    _converter = DocumentConverter()
  return _converter


def document_source_to_markdown(source: str, max_chars: int = 80000) -> str:
  """
  Run Docling on a file path or URL and return markdown text.

  Args:
    source: Path string or http(s) URL accepted by DocumentConverter.convert.
    max_chars: Maximum characters of markdown to return (longer output is truncated).

  Returns:
    Markdown body, or a string starting with "Error: " on failure.
  """
  try:
    result = _get_converter().convert(source)
    md = result.document.export_to_markdown() or ""
  except Exception as e:
    return f"Error: {e}"

  text = md.strip()
  if not text:
    text = "(No text could be extracted from the document.)"

  if len(text) > max_chars:
    text = text[:max_chars] + f"\n\n[Truncated at {max_chars} characters]"
  return text
