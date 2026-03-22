"""Modal for entering a git commit message with optional AI fill."""
from collections.abc import Awaitable, Callable

from rich.syntax import Syntax
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal, VerticalScroll
from textual.widgets import Label, Button, TextArea, Static
from textual.screen import ModalScreen

from components.utils.input_modal import truncate_preview_body


class CommitMessageModal(ModalScreen):
  """Staged diff (scrollable) + multiline message: Save, optional Fill with AI, Cancel."""

  BINDINGS = [("escape", "cancel", "Cancel")]

  def __init__(
    self,
    title: str,
    staged_diff: str,
    initial_value: str = "",
    fill_ai: Callable[[], Awaitable[str]] | None = None,
  ):
    super().__init__()
    self.title_text = title
    self.staged_diff = truncate_preview_body(staged_diff)
    self.initial_value = initial_value
    self.fill_ai = fill_ai

  def compose(self) -> ComposeResult:
    from components.utils.buttons import ActionButton

    syntax = Syntax(
      self.staged_diff,
      lexer="diff",
      theme="monokai",
      line_numbers=True,
      word_wrap=False,
    )
    with Vertical(id="commit_message_modal_container"):
      yield Label("Staged diff", id="commit_diff_heading", markup=False)
      with VerticalScroll(id="commit_diff_scroll"):
        yield Static(syntax, id="commit_diff_static")
      yield Label(self.title_text, id="commit_message_heading", markup=False)
      yield TextArea(self.initial_value, id="commit_message_modal_input", classes="commit-message-body")
      with Horizontal(classes="modal-button-container commit-message-modal-buttons"):
        yield ActionButton(
          "Save",
          action=self.on_save,
          id="btn_commit_modal_save",
          variant="primary",
          classes="action-btn modal-button",
        )
        if self.fill_ai:
          yield ActionButton(
            "Fill with AI",
            action=self.on_fill_ai_click,
            id="btn_commit_modal_fill_ai",
            variant="default",
            classes="action-btn modal-button",
            tooltip="Generate a message from staged diff",
          )
        yield ActionButton(
          "Cancel",
          action=self.on_cancel,
          id="btn_commit_modal_cancel",
          variant="error",
          classes="action-btn modal-button",
        )

  def action_cancel(self) -> None:
    self.on_cancel()

  def on_mount(self) -> None:
    def focus_message_input() -> None:
      try:
        self.query_one("#commit_message_modal_input", TextArea).focus()
      except Exception:
        pass

    self.call_after_refresh(focus_message_input)

  def on_save(self) -> None:
    val = self.query_one("#commit_message_modal_input", TextArea).text
    self.dismiss(val)

  def on_cancel(self) -> None:
    self.dismiss(None)

  def on_fill_ai_click(self) -> None:
    if not self.fill_ai:
      return
    self.app.run_worker(self._run_fill_ai())

  async def _run_fill_ai(self) -> None:
    if not self.fill_ai:
      return
    try:
      btn = self.query_one("#btn_commit_modal_fill_ai", Button)
    except Exception:
      btn = None
    if btn is not None:
      btn.disabled = True
    try:
      text = await self.fill_ai()
      self.query_one("#commit_message_modal_input", TextArea).text = text
    except Exception as e:
      self.app.notify(str(e), severity="error")
    finally:
      if btn is not None:
        btn.disabled = False
