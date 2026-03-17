"""Read-only modal for viewing git diffs with colored output."""
from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Label, Button, Static
from textual.screen import ModalScreen
from textual import on
from rich.syntax import Syntax


class DiffModal(ModalScreen):
  """Read-only diff viewer modal with colored adds/removes and syntax highlighting."""

  DEFAULT_CSS = """
  DiffModal {
    align: center middle;
  }

  #diff_modal_container {
    width: 50%;
    height: auto;
    background: $panel;
    border: round $primary;
    padding: 1;
  }

  #diff_modal_header {
    height: auto;
    margin-bottom: 1;
  }

  #diff_modal_content {
    height: auto;
    overflow: auto;
    scrollbar-size: 1 1;
    padding: 1;
  }

  #diff_modal_content Static {
    width: auto;
    min-width: 100%;
  }
  """

  def __init__(self, title: str, content: str, file_path: str | None = None, **kwargs):
    super().__init__(**kwargs)
    self.title_text = title
    self.content = content
    self.file_path = file_path

  def compose(self) -> ComposeResult:
    syntax = Syntax(
      self.content,
      lexer="diff",
      theme="monokai",
      line_numbers=True,
      word_wrap=False,
    )
    with Vertical(id="diff_modal_container"):
      yield Label(self.title_text, id="diff_modal_header")
      with VerticalScroll(id="diff_modal_content"):
        yield Static(syntax)
      yield Button("Close", id="btn_diff_close", variant="primary")

  @on(Button.Pressed, "#btn_diff_close")
  def on_close(self) -> None:
    self.dismiss()
