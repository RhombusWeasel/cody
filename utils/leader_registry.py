"""
Mergeable tree of leader chords. Duplicate paths: last registration wins.

Init order (see main.py): reset_leader_registry() → register_core_leader_chords()
→ load tools (optional register at import) → discover_leader_entries() for skills.
"""
from __future__ import annotations

import importlib.util
import sys
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from utils.skills import skill_manager

if TYPE_CHECKING:
  from textual.app import App

Handler = Callable[["App"], Awaitable[None] | None]


@dataclass
class LeaderNode:
  """Branch: label + children. Leaf: label + handler (children empty)."""
  label: str
  children: dict[str, LeaderNode] = field(default_factory=dict)
  handler: Handler | None = None


_root: LeaderNode = LeaderNode("", {})


def _norm_key(key: str) -> str:
  if len(key) != 1:
    raise ValueError(f"leader key must be a single character, got {key!r}")
  return key.lower()


def reset_leader_registry() -> None:
  global _root
  _root = LeaderNode("", {})


def _ensure_branch(parent_keys: Sequence[str]) -> LeaderNode:
  node = _root
  for k in parent_keys:
    kk = _norm_key(k)
    if kk not in node.children:
      node.children[kk] = LeaderNode("", {})
    child = node.children[kk]
    if child.handler is not None:
      child.handler = None
    node = child
  return node


def register_submenu(parent_keys: Sequence[str], key: str, label: str) -> None:
  """Declare a submenu at parent_keys + key with display label."""
  parent = _ensure_branch(parent_keys)
  kk = _norm_key(key)
  if kk in parent.children:
    existing = parent.children[kk]
    existing.label = label
    existing.handler = None
  else:
    parent.children[kk] = LeaderNode(label, {})


def register_action(
  parent_keys: Sequence[str],
  key: str,
  label: str,
  handler: Handler,
) -> None:
  """Leaf action at parent_keys + key. Last write wins; replaces submenu."""
  parent = _ensure_branch(parent_keys)
  kk = _norm_key(key)
  parent.children[kk] = LeaderNode(label, {}, handler)


def get_leader_root() -> LeaderNode:
  return _root


class LeaderRegistrar:
  """Passed to skill register_leader(reg)."""

  def add_submenu(self, parent_keys: Sequence[str], key: str, label: str) -> None:
    register_submenu(parent_keys, key, label)

  def add_action(
    self,
    parent_keys: Sequence[str],
    key: str,
    label: str,
    handler: Handler,
  ) -> None:
    register_action(parent_keys, key, label, handler)


def register_core_leader_chords() -> None:
  """Register built-in leader chords from workspace, chat, and terminal/sidebar modules."""
  from components.chat.chat import register_leader_chords as reg_chat
  from components.terminal.terminal_sidebar import register_leader_chords as reg_terminal
  from components.workspace.workspace import register_leader_chords as reg_workspace

  reg = LeaderRegistrar()
  reg_workspace(reg)
  reg_chat(reg)
  reg_terminal(reg)


def register_builtin_leader_chords() -> None:
  """Backward-compatible alias for register_core_leader_chords."""
  register_core_leader_chords()


def discover_leader_entries() -> None:
  """Load components/leader_menu.py from each skill and call register_leader(reg)."""
  skill_manager.discover_skills()
  for name, skill in skill_manager.skills.items():
    base_dir = Path(skill["base_dir"])
    leader_path = base_dir / "components" / "leader_menu.py"
    if not leader_path.exists():
      continue
    inserted_path = None
    skill_scripts = base_dir / "scripts"
    if skill_scripts.exists():
      inserted_path = str(skill_scripts)
      sys.path.insert(0, inserted_path)
    try:
      mod_name = f"skill_leader_{name.replace('-', '_')}"
      spec = importlib.util.spec_from_file_location(mod_name, leader_path)
      if not spec or not spec.loader:
        continue
      module = importlib.util.module_from_spec(spec)
      spec.loader.exec_module(module)
      fn = getattr(module, "register_leader", None)
      if callable(fn):
        fn(LeaderRegistrar())
    except Exception as e:
      print(f"Error loading leader menu for skill {name}: {e}")
    finally:
      if inserted_path and inserted_path in sys.path:
        sys.path.remove(inserted_path)
