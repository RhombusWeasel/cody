"""Vault tree rows: secret value line shown under an expanded entry branch."""

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Input, Label, TextArea
from textual.widget import Widget


def _mask_note_body(text: str) -> str:
  if not text:
    return ""
  lines = text.split("\n")
  out: list[str] = []
  for line in lines:
    if not line:
      out.append("•")
    else:
      out.append("•" * min(len(line), 56))
  return "\n".join(out)


class VaultSecretLineRow(Widget):
  """Indented row: password Input or note TextArea (read-only), no actions."""


  def __init__(
    self,
    indent: str,
    secret_value: str,
    revealed: bool,
    is_note: bool,
    **kwargs,
  ):
    super().__init__(**kwargs)
    self.indent = indent
    self.secret_value = secret_value
    self.revealed = revealed
    self.is_note = is_note

  def compose(self) -> ComposeResult:
    with Horizontal(classes="vault-secret-line"):
      yield Label(self.indent, classes="tree-indent", markup=False)
      if self.is_note:
        shown = self.secret_value if self.revealed else _mask_note_body(self.secret_value)
        yield TextArea(shown, disabled=True, classes="vault-note-body")
      else:
        yield Input(
          self.secret_value,
          disabled=True,
          password=not self.revealed,
          classes="vault-secret-input",
        )
