"""Slash command: copy repo docs/*.md into this skill's reference/ (same as run_skill script)."""

import importlib.util
from pathlib import Path

from utils.cmd_loader import CommandBase


def _sync_module():
  skill_root = Path(__file__).resolve().parent.parent
  script_path = skill_root / "scripts" / "sync_reference_docs.py"
  spec = importlib.util.spec_from_file_location(
    "cody_skill_author_sync_reference_docs",
    script_path,
  )
  if not spec or not spec.loader:
    raise ImportError(f"Cannot load {script_path}")
  mod = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(mod)
  return mod, skill_root


class SyncReferenceDocsCommand(CommandBase):
  description = "Copy docs/extending_cody.md, utils_reference.md, password_vault.md into cody-skill-author/reference/"

  async def execute(self, app, args: list[str]):
    try:
      mod, skill_root = _sync_module()
      code, lines = mod.copy_canonical_docs_to_reference(skill_root / "reference")
      msg = "\n".join(lines)
      if code != 0:
        app.notify(msg, severity="warning")
      else:
        app.notify(msg)
    except Exception as e:
      app.notify(f"sync_reference_docs failed: {e}", severity="error")
      print(f"sync_reference_docs command failed: {e}")
