"""File system operations for the file tree component."""
import re
import shutil
import warnings
from pathlib import Path

from utils.cfg_man import cfg
from utils.tree_model import TreeEntry
from utils.icons import FOLDER, FILE, FILE_ICONS

_warned_bad_exclude_patterns: set[str] = set()


def _compiled_name_exclude_patterns() -> list[re.Pattern]:
  raw = cfg.get("file_tree.name_exclude_patterns", [])
  if not isinstance(raw, list):
    return []
  out: list[re.Pattern] = []
  for p in raw:
    if not isinstance(p, str) or not p.strip():
      continue
    try:
      out.append(re.compile(p))
    except re.error as e:
      if p not in _warned_bad_exclude_patterns:
        _warned_bad_exclude_patterns.add(p)
        warnings.warn(
          f"Invalid file_tree.name_exclude_patterns regex {p!r}: {e}",
          UserWarning,
          stacklevel=2,
        )
  return out


def _name_excluded(name: str, patterns: list[re.Pattern]) -> bool:
  return any(pat.fullmatch(name) for pat in patterns)


def path_entries_to_tree(
  result: list[TreeEntry],
  parent: Path,
  prefix: str,
  expanded: set,
  branch: str,
  last_branch: str,
  vertical: str,
  spacer: str,
  folder_icon: str | None = None,
  file_icon: str | None = None,
  file_icons: dict[str, str] | None = None,
) -> None:
  """Append file-tree entries for parent dir to result. Recurses when dir is expanded."""
  folder = folder_icon or FOLDER
  file_default = file_icon or FILE
  ext_icons = file_icons or FILE_ICONS
  entries = list_dir(parent)
  for i, (name, is_dir) in enumerate(entries):
    path = parent / name
    is_last = i == len(entries) - 1
    sym = last_branch if is_last else branch
    is_expanded = path in expanded
    icon = folder if is_dir else ext_icons.get(path.suffix.lower(), file_default)
    display_name = path.name or str(path)
    result.append(TreeEntry(
      node_id=path,
      indent=prefix + sym,
      is_expandable=is_dir,
      is_expanded=is_expanded,
      display_name=display_name,
      icon=icon,
    ))
    if is_dir and is_expanded:
      ext = spacer if is_last else vertical
      path_entries_to_tree(
        result, path, prefix + ext, expanded, branch, last_branch, vertical, spacer,
        folder_icon=folder, file_icon=file_default, file_icons=ext_icons,
      )


def list_dir(path: Path) -> list[tuple[str, bool]]:
  """List directory contents. Returns (name, is_dir) sorted with dirs first."""
  if not path.is_dir():
    return []
  patterns = _compiled_name_exclude_patterns()
  entries = []
  for p in path.iterdir():
    if _name_excluded(p.name, patterns):
      continue
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
