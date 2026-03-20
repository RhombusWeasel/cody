"""File editing utilities - language mapping and editor tab."""
import asyncio
import threading
from pathlib import Path
from typing import Callable


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
  """Open EditorTab to edit a file. Handles read errors."""
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

  from components.workspace.editor_tab import EditorTab
  from components.workspace.workspace import Workspace

  editor_tab = EditorTab(
      path=path,
      content=content,
      language=language,
      code_editor=bool(code_editor),
      on_saved=on_saved
  )

  def schedule_add_tab() -> None:
    async def add_tab() -> None:
      workspace = app.query_one(Workspace)
      await workspace.add_tab(editor_tab)

    asyncio.create_task(add_tab())

  try:
    app.query_one(Workspace)
  except Exception as e:
    app.notify(f"Could not open editor in workspace: {e}", severity="error")
    return

  # call_from_thread must only be used from a worker thread; on the main thread use call_later.
  if threading.current_thread() is threading.main_thread():
    app.call_later(schedule_add_tab)
  else:
    app.call_from_thread(schedule_add_tab)
