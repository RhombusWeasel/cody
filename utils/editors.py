"""File editing utilities - language mapping and editor modal."""
from pathlib import Path
from typing import Callable

from components.utils.input_modal import InputModal


LANG_MAP = {
  ".py": "python", ".lua": "lua", ".js": "javascript", ".ts": "typescript",
  ".html": "html", ".css": "css", ".json": "json", ".md": "markdown",
  ".sh": "bash", ".yaml": "yaml", ".yml": "yaml", ".toml": "toml",
  ".rs": "rust", ".go": "go", ".c": "c", ".cpp": "cpp", ".h": "c",
  ".hpp": "cpp", ".java": "java",
}


def open_file_editor(
  app,
  path: Path,
  on_saved: Callable[[], None] | None = None,
) -> None:
  """Open InputModal to edit a file. Handles read/save errors. Calls on_saved after save."""
  try:
    content = path.read_text(encoding="utf-8")
  except UnicodeDecodeError:
    app.notify("Not a text file", severity="warning")
    return
  except Exception as e:
    app.notify(f"Error reading: {e}", severity="error")
    return

  ext = path.suffix.lower()
  language = LANG_MAP.get(ext)
  code_editor = ext in LANG_MAP

  def on_result(new_content: str | None) -> None:
    if new_content is not None:
      try:
        path.write_text(new_content, encoding="utf-8")
        app.notify(f"Saved {path.name}")
        if on_saved:
          on_saved()
      except Exception as e:
        app.notify(f"Error saving: {e}", severity="error")

  app.push_screen(
    InputModal(
      title=f"Editing {path.name}",
      initial_value=content,
      multiline=True,
      language=language,
      code_editor=bool(code_editor),
    ),
    on_result,
  )
