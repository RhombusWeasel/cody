"""Read-only modal for viewing git diffs with colored output."""
from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Label, Button, Static
from textual.screen import ModalScreen
from textual import on
from rich.syntax import Syntax


class DiffModal(ModalScreen):
  """Read-only diff viewer modal with colored adds/removes and syntax highlighting."""


  def __init__(self, title: str, content: str, file_path: str | None = None, **kwargs):
    super().__init__(**kwargs)
    self.title_text = title
    self.content = content
    self.file_path = file_path

  def compose(self) -> ComposeResult:
    from components.utils.buttons import ActionButton
    syntax = Syntax(
      self.content,
      lexer="diff",
      theme="monokai",
      line_numbers=True,
      word_wrap=False,
    )
    with Vertical(id="diff_modal_container"):
      yield Label(self.title_text, id="diff_modal_header", markup=False)
      with VerticalScroll(id="diff_modal_content"):
        yield Static(syntax)
      yield ActionButton("Close", action=self.on_close, id="btn_diff_close", variant="primary", classes="action-btn")

  def on_close(self) -> None:
    self.dismiss()
