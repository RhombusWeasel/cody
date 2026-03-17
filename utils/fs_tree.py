"""File system operations for the file tree component."""
import shutil
from pathlib import Path


def list_dir(path: Path) -> list[tuple[str, bool]]:
  """List directory contents. Returns (name, is_dir) sorted with dirs first."""
  if not path.is_dir():
    return []
  entries = []
  for p in path.iterdir():
    try:
      entries.append((p.name, p.is_dir()))
    except OSError:
      # Include entry anyway (e.g. permission denied) - assume file if we can't stat
      entries.append((p.name, False))
  entries.sort(key=lambda x: (not x[1], x[0].lower()))
  return entries


def create_file(path: Path, content: str = "") -> bool:
  """Create a file. Returns True on success."""
  try:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True
  except OSError:
    return False


def create_dir(path: Path) -> bool:
  """Create a directory. Returns True on success."""
  try:
    path.mkdir(parents=True, exist_ok=True)
    return True
  except OSError:
    return False


def delete_path(path: Path) -> bool:
  """Delete a file or directory. Refuses to delete cwd. Returns True on success."""
  try:
    cwd = Path.cwd().resolve()
    resolved = path.resolve()
    if resolved == cwd or cwd.is_relative_to(resolved):
      return False
    if path.is_dir():
      shutil.rmtree(path)
    else:
      path.unlink()
    return True
  except OSError:
    return False
