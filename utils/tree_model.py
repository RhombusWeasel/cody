"""Tree entry model for generic tree components."""
from dataclasses import dataclass
from typing import Any


@dataclass
class TreeEntry:
  """Single visible row in a flat tree."""

  node_id: Any
  indent: str
  is_expandable: bool
  is_expanded: bool
  display_name: str
  icon: str
