from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, Horizontal, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Label, Markdown

from components.utils.buttons import ActionButton


class CommandsHelpModal(ModalScreen[None]):
  """Scrollable markdown list of slash commands; Esc closes."""

  BINDINGS = [
    Binding("escape", "close", "Close", show=False),
  ]
  CSS_PATH = "commands_help_modal.css"

  def __init__(self, markdown_body: str) -> None:
    super().__init__()
    self._markdown_body = markdown_body

  def compose(self) -> ComposeResult:
    with Vertical(id="commands_help_modal_container"):
      yield Label("Available commands", id="commands_help_modal_title")
      with VerticalScroll(id="commands_help_modal_scroll"):
        yield Markdown(self._markdown_body, id="commands_help_modal_body")
      with Horizontal(classes="modal-button-container"):
        yield ActionButton(
          "Close",
          action=self.action_close,
          id="btn_commands_help_close",
          variant="primary",
          classes="action-btn modal-button",
        )

  def on_mount(self) -> None:
    self.query_one("#commands_help_modal_scroll").focus()

  def action_close(self) -> None:
    self.dismiss(None)
