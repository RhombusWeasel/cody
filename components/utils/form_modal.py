"""Schema-driven form modal. Pass a schema, args dict, and callback to collect structured input."""
from typing import Callable

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal, VerticalScroll
from textual.widgets import Label, Input, Button, TextArea
from textual.screen import ModalScreen
from textual import on


class FormModal(ModalScreen):
  """
  A generic form modal driven by a schema list.

  Schema field types:
    text     — single-line Input
    textarea — multi-line TextArea
    code     — code editor TextArea (add "language" key for syntax highlighting)
    row      — side-by-side group; use "fields" key with a list of child field dicts

  args: dict of initial values (keyed by field "key") plus any extra data to
        pass through. On Save the form values are merged over args and the result
        is passed to callback. On Cancel the callback is not called.
  """

  def __init__(self, title: str, schema: list[dict], args: dict | None = None, callback: Callable | None = None):
    super().__init__()
    self._title = title
    self._schema = schema
    self._args = args or {}
    self._callback = callback

  def compose(self) -> ComposeResult:
    with Vertical(id="form_modal_container"):
      yield Label(self._title, id="form_modal_title")
      with VerticalScroll(id="form_modal_body"):
        yield from self._compose_fields(self._schema)
      with Horizontal(classes="modal-button-container"):
        from components.utils.buttons import ActionButton
        yield ActionButton("Save", action=self.on_save, id="btn_form_save", variant="primary", classes="action-btn modal-button")
        yield ActionButton("Cancel", action=self.on_cancel, id="btn_form_cancel", variant="error", classes="action-btn modal-button")

  def _compose_fields(self, fields: list[dict]) -> ComposeResult:
    for field in fields:
      field_type = field.get("type", "text")
      if field_type == "row":
        with Horizontal(classes="form-modal-row"):
          for child in field.get("fields", []):
            with Vertical(classes="form-modal-col"):
              yield from self._render_field(child)
      else:
        yield from self._render_field(field)

  def _render_field(self, field: dict) -> ComposeResult:
    key = field["key"]
    label = field.get("label", key)
    field_type = field.get("type", "text")
    placeholder = field.get("placeholder", "")
    initial = str(self._args.get(key, "") or "")
    widget_id = f"form_field_{key}"

    yield Label(label, classes="field-label")

    if field_type == "code":
      yield TextArea.code_editor(initial, id=widget_id, language=field.get("language"))
    elif field_type == "textarea":
      yield TextArea(initial, id=widget_id)
    else:
      yield Input(initial, id=widget_id, placeholder=placeholder)

  def on_mount(self) -> None:
    first_input = next(iter(self.query(Input)), None)
    if first_input:
      first_input.focus()

  def _collect_values(self) -> dict:
    result = {}
    for field in self._schema:
      if field.get("type") == "row":
        for child in field.get("fields", []):
          result[child["key"]] = self._read_field(child)
      else:
        result[field["key"]] = self._read_field(field)
    return result

  def _read_field(self, field: dict) -> str:
    key = field["key"]
    field_type = field.get("type", "text")
    widget_id = f"form_field_{key}"
    if field_type in ("textarea", "code"):
      return self.query_one(f"#{widget_id}", TextArea).text
    return self.query_one(f"#{widget_id}", Input).value

  def on_save(self) -> None:
    required_fields = [
      f for f in self._schema
      if f.get("type") != "row" and f.get("required")
    ]
    for field in required_fields:
      val = self._read_field(field)
      if not val.strip():
        self.app.notify(f"{field.get('label', field['key'])} is required.", severity="error")
        return

    values = self._collect_values()
    merged = {**self._args, **values}
    if self._callback:
      self._callback(merged)
    self.dismiss(None)

  def on_cancel(self) -> None:
    self.dismiss(None)
