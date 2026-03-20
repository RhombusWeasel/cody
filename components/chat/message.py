import json
import re

from textual import on
from textual.widget import Widget
from textual.widgets import Markdown, Collapsible, LoadingIndicator, Button


def _extract_result(result) -> str:
  """Extract displayable result, handling nested JSON from tools that return full objects."""
  if not result:
    return ""
  if isinstance(result, str):
    try:
      nested = json.loads(result)
      if isinstance(nested, dict) and "result" in nested:
        return _extract_result(nested["result"])
    except (json.JSONDecodeError, TypeError):
      pass
    return result
  return json.dumps(result, indent=2)


def _parse_tool_block(content: str) -> dict | None:
  """Parse tool JSON. Returns {function, arguments, result} or None."""
  try:
    data = json.loads(content)
    return {
      'function': data.get('function', 'unknown_tool'),
      'arguments': data.get('arguments', {}),
      'result': _extract_result(data.get('result', ''))
    }
  except (json.JSONDecodeError, AttributeError, TypeError):
    return None


def _args_to_markdown_table(args: dict) -> str:
  """Build a markdown table from arguments dict."""
  if not args:
    return ""
  rows = ["| Argument | Value |", "| --- | --- |"]
  for k, v in args.items():
    val = str(v) if not isinstance(v, (dict, list)) else json.dumps(v)
    val = val.replace("|", "\\|").replace("\n", " ")
    rows.append(f"| {k} | {val} |")
  return "\n".join(rows)


def _format_result(result) -> str:
  """Format result for markdown display."""
  if not result:
    return ""
  if not isinstance(result, str):
    result = json.dumps(result, indent=2)
  return f"**Result:**\n\n```\n{result}\n```"


def _render_text_block(content: str):
  """Yield Markdown widgets for text, handling file attachments."""
  if not content:
    return
  parts = re.split(r'\n\n`([^`]+)`:\n```[a-zA-Z0-9]*\n([\s\S]*?)\n```', content)
  if len(parts) > 1:
    if parts[0].strip():
      md = Markdown(parts[0])
      md.code_indent_guides = False
      yield md
    for i in range(1, len(parts), 3):
      filename = parts[i]
      file_content = parts[i+1]
      text_after = parts[i+2] if i+2 < len(parts) else ""
      ext = filename.split('.')[-1] if '.' in filename else 'text'
      with Collapsible(title=f"File: {filename}", classes="file-attachment", collapsed=True):
        md = Markdown(f"```{ext}\n{file_content}\n```")
        md.code_indent_guides = False
        yield md
      if text_after.strip():
        md = Markdown(text_after)
        md.code_indent_guides = False
        yield md
  else:
    md = Markdown(content)
    md.code_indent_guides = False
    yield md


class Message(Widget):
  def __init__(self, role: str, blocks: list, git_checkpoint: str | None = None):
    super().__init__()
    self.role = role
    self.title = role
    self.border_title = role
    self.blocks = blocks
    self.git_checkpoint = git_checkpoint
    self.loading = any(b.get('loading') for b in blocks if b['type'] == 'text')

  def compose(self):
    from components.utils.buttons import ActionButton
    with Collapsible(title=self.title, classes=self.title, collapsed=False):
      if self.role == "user" and self.git_checkpoint:
        short_hash = self.git_checkpoint[:7] if len(self.git_checkpoint) >= 7 else self.git_checkpoint
        yield ActionButton(f"Revert to here ({short_hash})", action=self.on_revert_pressed, id="revert_btn", variant="warning", classes="action-btn revert-btn")
      for block in self.blocks:
        if block['type'] == 'text':
          if block.get('loading'):
            yield LoadingIndicator()
          if block.get('content'):
            yield from _render_text_block(block['content'])
        elif block['type'] == 'tool':
          parsed = _parse_tool_block(block['content'])
          if parsed is None:
            md = Markdown(block['content'])
            md.code_indent_guides = False
            yield md
            continue
          func = parsed['function']
          args = parsed['arguments']
          result = parsed['result']
          is_standalone = self.role == 'tool' and len(self.blocks) == 1
          content_parts = []
          if args:
            content_parts.append(_args_to_markdown_table(args))
          if result:
            content_parts.append(_format_result(result))
          content = "\n\n".join(content_parts) or "(no output)"
          if is_standalone:
            with Collapsible(title=func, classes="tool", collapsed=False):
              md = Markdown(content)
              md.code_indent_guides = False
              yield md
          else:
            with Collapsible(title=func, classes="tool", collapsed=True):
              md = Markdown(content)
              md.code_indent_guides = False
              yield md

  def on_revert_pressed(self) -> None:
    if not self.git_checkpoint:
      return
    from components.utils.input_modal import InputModal
    from components.chat.chat import MsgBox
    from components.chat.input import MessageInput
    from utils.cfg_man import cfg
    from utils.git import revert_to_checkpoint
    import asyncio
    wd = cfg.get("session.working_directory")
    commit_hash = self.git_checkpoint
    content = self.blocks[0].get("content", "") if self.blocks else ""
    raw_query = content.split("\n\n`")[0].strip() if "\n\n`" in content else content
    node = self.parent
    msg_box = None
    while node:
      if isinstance(node, MsgBox):
        msg_box = node
        break
      node = getattr(node, "parent", None)

    def on_confirm(confirmed: bool | None) -> None:
      if not confirmed or not msg_box:
        return

      async def _do_revert() -> None:
        await asyncio.to_thread(revert_to_checkpoint, wd, commit_hash)
        idx = None
        for i, m in enumerate(msg_box.actor.msg):
          if m.get("git_checkpoint") == commit_hash:
            idx = i
            break
        if idx is None:
          return
        msg_box.actor.msg = msg_box.actor.msg[:idx]
        show_system = msg_box.config.get("interface.show_system_messages", False)
        msg_box.messages = msg_box.actor.msg if show_system else [m for m in msg_box.actor.msg if m.get("role") != "system"]
        try:
          inp = msg_box.query_one(MessageInput)
          inp.value = raw_query
        except Exception:
          pass
        await msg_box.save_chat()
        msg_box._refresh_chat_history()

      self.app.run_worker(_do_revert())

    self.app.push_screen(
      InputModal("Revert working tree to this checkpoint? This will overwrite uncommitted changes.", confirm_only=True),
      on_confirm,
    )
