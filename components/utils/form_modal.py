"""Schema-driven form modal. Pass a schema, args dict, and callback to collect structured input."""
from typing import Callable, Iterator

from textual.app import ComposeResult
from textual.containers import Vertical, VerticalGroup, Horizontal, VerticalScroll
from textual.widgets import Label, Input, TextArea, Select
from textual.screen import ModalScreen
from textual import on


class FormModal(ModalScreen):
  """
  A generic form modal driven by a schema list.

  Schema field types:
    text     — single-line Input
    textarea — multi-line TextArea
    code     — code editor TextArea (add "language" key for syntax highlighting)
    password — masked Input
    select   — Select (``options`` list of string values)
    row      — side-by-side group; use "fields" key with a list of child field dicts

  Optional ``show_when: {"key": "<field_key>", "value": "<str>"}`` hides the field
  unless the controlling field's current value matches (widgets stay mounted).

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

  def _iter_flat_fields(self) -> Iterator[dict]:
    for field in self._schema:
      if field.get("type") == "row":
        for child in field.get("fields", []):
          yield child
      else:
        yield field

  def _schema_field_by_key(self, key: str) -> dict | None:
    for f in self._iter_flat_fields():
      if f["key"] == key:
        return f
    return None

  def _field_visible(self, field: dict) -> bool:
    sw = field.get("show_when")
    if not sw:
      return True
    ctl_key = sw["key"]
    expected = str(sw["value"])
    ctl_field = self._schema_field_by_key(ctl_key)
    if not ctl_field:
      return True
    try:
      actual = self._read_field(ctl_field).strip()
    except Exception:
      return False
    return actual == expected

  def _sync_conditional_visibility(self) -> None:
    for field in self._iter_flat_fields():
      if not field.get("show_when"):
        continue
      key = field["key"]
      try:
        wrap = self.query_one(f"#form_field_wrap_{key}", VerticalGroup)
      except Exception:
        continue
      wrap.display = self._field_visible(field)

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

    def inner() -> ComposeResult:
      yield Label(label, classes="field-label")
      if field_type == "code":
        yield TextArea.code_editor(initial, id=widget_id, language=field.get("language"))
      elif field_type == "textarea":
        yield TextArea(initial, id=widget_id)
      elif field_type == "password":
        yield Input(initial, id=widget_id, placeholder=placeholder, password=True)
      elif field_type == "select":
        opts = [str(o) for o in field.get("options", [])]
        pairs = [(o, o) for o in opts]
        allow_blank = not field.get("required", False)
        if initial and initial in opts:
          sel_val = initial
        elif opts and field.get("required"):
          sel_val = opts[0]
        else:
          sel_val = Select.BLANK
        yield Select(pairs, value=sel_val, allow_blank=allow_blank, id=widget_id)
      else:
        yield Input(initial, id=widget_id, placeholder=placeholder)

    if field.get("show_when"):
      # VerticalGroup: height auto — plain Vertical defaults to height 1fr and splits scroll viewport.
      with VerticalGroup(id=f"form_field_wrap_{key}", classes="form-field-conditional"):
        yield from inner()
    else:
      yield from inner()

  def on_mount(self) -> None:
    self._sync_conditional_visibility()
    for inp in self.query(Input):
      if inp.visible:
        inp.focus()
        break

  @on(Select.Changed)
  def _on_any_select_changed(self, _event: Select.Changed) -> None:
    self._sync_conditional_visibility()

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
    if field_type == "select":
      w = self.query_one(f"#{widget_id}", Select)
      v = w.value
      if v is Select.BLANK:
        return ""
      return str(v)
    return self.query_one(f"#{widget_id}", Input).value

  def on_save(self) -> None:
    required_fields = [f for f in self._iter_flat_fields() if f.get("required")]
    for field in required_fields:
      if not self._field_visible(field):
        continue
      val = self._read_field(field)
      if field.get("type") == "select":
        if not val.strip():
          self.app.notify(f"{field.get('label', field['key'])} is required.", severity="error")
          return
      elif not val.strip():
        self.app.notify(f"{field.get('label', field['key'])} is required.", severity="error")
        return

    values = self._collect_values()
    merged = {**self._args, **values}
    if self._callback:
      self._callback(merged)
    self.dismiss(None)

  def on_cancel(self) -> None:
    self.dismiss(None)
