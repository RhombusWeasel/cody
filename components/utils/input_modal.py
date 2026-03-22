import asyncio

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Label, Input, TextArea
from textual.screen import ModalScreen
from textual import on


def truncate_preview_body(body: str, max_chars: int = 48_000) -> str:
  if len(body) <= max_chars:
    return body
  return body[:max_chars] + "\n\n--- (truncated for preview) ---"


class PreviewToChatModal(ModalScreen):
  """Read-only preview; dismiss(True) to insert into chat, dismiss(None) to cancel."""

  BINDINGS = [("escape", "cancel", "Cancel")]

  def __init__(self, title: str, body: str):
    super().__init__()
    self.title_text = title
    self.body = body

  def compose(self) -> ComposeResult:
    with Vertical(id="preview_to_chat_container"):
      yield Label(self.title_text)
      yield TextArea(
        self.body,
        id="preview_to_chat_body",
        classes="preview-to-chat-body",
        read_only=True,
      )
      with Horizontal(classes="modal-button-container"):
        from components.utils.buttons import ActionButton
        yield ActionButton(
          "Add to chat",
          action=self._on_add,
          id="btn_preview_to_chat_add",
          variant="primary",
          classes="action-btn modal-button",
        )
        yield ActionButton(
          "Cancel",
          action=self._on_cancel,
          id="btn_preview_to_chat_cancel",
          variant="error",
          classes="action-btn modal-button",
        )

  def action_cancel(self) -> None:
    self.dismiss(None)

  def _on_add(self) -> None:
    self.dismiss(True)

  def _on_cancel(self) -> None:
    self.dismiss(None)

  def on_mount(self) -> None:
    def focus_preview_body() -> None:
      try:
        self.query_one("#preview_to_chat_body", TextArea).focus()
      except Exception:
        pass

    self.call_after_refresh(focus_preview_body)


async def preview_then_append_chat_message(
  app,
  title: str,
  body: str,
  *,
  role: str = "system",
) -> None:
  """Show preview modal; on confirm append message to active chat and save."""
  from components.workspace.workspace import Workspace

  workspace = app.query_one(Workspace)
  if not workspace.get_active_msg_box():
    app.notify("No active chat tab.", severity="warning")
    return

  body = truncate_preview_body(body)
  loop = asyncio.get_running_loop()
  fut = loop.create_future()

  def on_dismiss(result):
    loop.call_soon_threadsafe(fut.set_result, result)

  def push_preview():
    app.push_screen(PreviewToChatModal(title, body), on_dismiss)

  # Defer past the key event that submitted the slash command; otherwise Enter
  # activates the first focused button ("Add to chat") in the same tick.
  app.call_later(push_preview)
  confirmed = await fut
  if not confirmed:
    return

  msg_box = workspace.get_active_msg_box()
  if not msg_box:
    return

  show_system = msg_box.config.get("interface.show_system_messages", False)
  effective_role = role
  content = body
  if role == "system" and not show_system:
    effective_role = "user"
    content = f"*(command output)*\n\n{body}"

  msg_box.actor.msg.append({"role": effective_role, "content": content})
  src = msg_box.actor.msg
  msg_box.messages = src if show_system else [m for m in src if m.get("role") != "system"]
  await msg_box.save_chat()
  msg_box._refresh_chat_history()

class InputModal(ModalScreen):

  def __init__(
    self,
    title: str,
    initial_value: str = "",
    multiline: bool = False,
    language: str | None = None,
    code_editor: bool = False,
    confirm_only: bool = False,
    password: bool = False,
  ):
    super().__init__()
    self.title_text = title
    self.initial_value = initial_value
    self.multiline = multiline
    self.language = language
    self.code_editor = code_editor
    self.confirm_only = confirm_only
    self.password = password

  def compose(self) -> ComposeResult:
    with Vertical(id="input_modal_container"):
      yield Label(self.title_text)
      if not self.confirm_only:
        if self.code_editor and self.language:
          yield TextArea.code_editor(self.initial_value, id="input_modal_input", language=self.language)
        elif self.multiline:
          yield TextArea(self.initial_value, id="input_modal_input", language=self.language)
        else:
          yield Input(self.initial_value, id="input_modal_input", password=self.password)
      with Horizontal(classes="modal-button-container"):
        from components.utils.buttons import ActionButton
        if self.confirm_only:
          yield ActionButton("Confirm", action=self.on_save, id="btn_input_modal_save", variant="primary", classes="action-btn modal-button")
        else:
          yield ActionButton("Save", action=self.on_save, id="btn_input_modal_save", variant="primary", classes="action-btn modal-button")
        yield ActionButton("Cancel", action=self.on_cancel, id="btn_input_modal_cancel", variant="error", classes="action-btn modal-button")

  def on_mount(self) -> None:
    if self.confirm_only:
      return
    if self.language == "lua" and (self.code_editor or self.multiline):
      try:
        import tree_sitter_lua
        from tree_sitter import Language
        from pathlib import Path

        text_area = self.query_one("#input_modal_input", TextArea)
        lua_lang = Language(tree_sitter_lua.language())
        highlights_path = Path(tree_sitter_lua.__file__).parent / "queries" / "highlights.scm"
        highlights = highlights_path.read_text()

        text_area.register_language("lua", lua_lang, highlights)
        text_area.language = ""
        text_area.language = "lua"
      except ImportError:
        pass

    def focus_modal_container() -> None:
      try:
        box = self.query_one("#input_modal_container")
        box.can_focus = True
        box.focus()
      except Exception:
        pass

    # Ghost Enter: submitting chat handles Enter in the same message pump turn as
    # push_screen; focus can land on Save/Input and that key (or a queued repeat)
    # is delivered to the new screen. Defer + focus a non-Input parent avoids Input.Submitted.
    self.call_after_refresh(focus_modal_container)

  @on(Input.Submitted, "#input_modal_input")
  def on_input_submitted(self) -> None:
    self.on_save()

  def on_save(self) -> None:
    if self.confirm_only:
      self.dismiss(True)
    elif self.multiline:
      val = self.query_one("#input_modal_input", TextArea).text
      self.dismiss(val)
    else:
      val = self.query_one("#input_modal_input", Input).value
      self.dismiss(val)

  def on_cancel(self) -> None:
    self.dismiss(None)
