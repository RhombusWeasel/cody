"""Backward-compat re-exports. Use components.tree for new code."""
from pathlib import Path

from components.tree.tree_row import TreeRow, NodeToggled, NodeSelected

FileSelected = NodeSelected
DirToggled = NodeToggled


class FileTreeRow(TreeRow):
  """Alias for TreeRow with Path-specific semantics. Prefer TreeRow."""

  def __init__(
    self,
    path: Path,
    indent: str,
    is_dir: bool,
    is_expanded: bool,
    button_factory,
    display_name: str | None = None,
    **kwargs,
  ):
    from utils.icons import FOLDER, FILE, FILE_ICONS
    icon = FOLDER if is_dir else FILE_ICONS.get(path.suffix.lower(), FILE)
    label = display_name if display_name is not None else (path.name or str(path))
    super().__init__(
      node_id=path,
      indent=indent,
      is_expandable=is_dir,
      is_expanded=is_expanded,
      display_name=label,
      icon=icon,
      button_factory=button_factory,
      **kwargs,
    )
