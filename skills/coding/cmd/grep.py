import os
import re

from utils.cmd_loader import CommandBase
from utils.cfg_man import cfg
from components.utils.input_modal import preview_then_append_chat_message

_MAX_TOTAL_LINES = 200
_MAX_PER_FILE = 40


def _search_in_file(file_path: str, pattern: str) -> list[tuple[int, str]]:
  try:
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
      content = f.read()
  except OSError:
    return []
  lines = content.split("\n")
  matches = []
  for i, line in enumerate(lines):
    if re.search(pattern, line):
      matches.append((i + 1, line))
  return matches


def _format_search(pattern: str, root: str) -> str:
  if not os.path.exists(root):
    return f"Error: path does not exist: {root}"
  lines_out: list[str] = [f"Searching for `{pattern}` in `{root}`:\n"]
  total_lines = 0
  truncated = False
  found_any = False

  if os.path.isfile(root):
    matches = _search_in_file(root, pattern)
    if matches:
      found_any = True
      lines_out.append(f"--- {root} ---")
      for line_num, line in matches[:_MAX_PER_FILE]:
        if total_lines >= _MAX_TOTAL_LINES:
          truncated = True
          break
        lines_out.append(f"{line_num:6}|{line}")
        total_lines += 1
      if len(matches) > _MAX_PER_FILE:
        lines_out.append(f"  … {_MAX_PER_FILE} of {len(matches)} matches in this file …")
      lines_out.append("")
    out = "\n".join(lines_out).rstrip()
    if not found_any:
      return out + "\n\nNo matches found."
    if truncated:
      out += "\n\n--- (truncated: global line cap) ---"
    return out

  for dirpath, dirnames, filenames in os.walk(root):
    if ".git" in dirnames:
      dirnames.remove(".git")
    dirnames[:] = [d for d in dirnames if not d.startswith(".")]
    for fname in filenames:
      if fname.startswith("."):
        continue
      file_path = os.path.join(dirpath, fname)
      matches = _search_in_file(file_path, pattern)
      if not matches:
        continue
      found_any = True
      lines_out.append(f"--- {file_path} ---")
      for line_num, line in matches[:_MAX_PER_FILE]:
        if total_lines >= _MAX_TOTAL_LINES:
          truncated = True
          break
        lines_out.append(f"{line_num:6}|{line}")
        total_lines += 1
      if len(matches) > _MAX_PER_FILE:
        lines_out.append(f"  … {_MAX_PER_FILE} of {len(matches)} matches in this file …")
      lines_out.append("")
      if truncated:
        break

  out = "\n".join(lines_out).rstrip()
  if not found_any:
    return out + "\n\nNo matches found."
  if truncated:
    out += "\n\n--- (truncated: global line cap) ---"
  return out


class GrepCommand(CommandBase):
  description = "Search workspace with regex (preview, then add to chat)"

  async def execute(self, app, args: list[str]):
    try:
      if not args:
        await preview_then_append_chat_message(app, "grep", "Usage: /grep <pattern>")
        return
      pattern = args[0]
      wd = cfg.get("session.working_directory", os.getcwd())
      body = _format_search(pattern, wd)
      await preview_then_append_chat_message(app, "grep", body)
    except re.error as e:
      await preview_then_append_chat_message(app, "grep", f"Invalid regex: {e}")
    except Exception as e:
      print(f"grep command failed: {e}")
