"""Postit sidebar — Postman-style HTTP requests from tiered JSON collections."""
import asyncio
import json

from textual import on, work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Input, Label, Select, TabbedContent, TabPane, TextArea

from components.utils.input_modal import InputModal
from skills.postit.scripts import postit_store
from utils.cfg_man import cfg
import utils.icons as icons

sidebar_label = icons.POSTIT
sidebar_tooltip = "HTTP requests (Postit)"


class PostitSidebarTab(VerticalScroll):
  """Load, edit, send, and save HTTP requests as JSON postits."""

  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self._suppress_reload = False
    self._merged: dict[str, dict] = {}

  def compose(self) -> ComposeResult:
    with Vertical(classes="postit-column"):
      yield Label(f"{icons.POSTIT} Postit", id="postit-title", classes="postit-title")
      with Horizontal(classes="postit-collection-row"):
        yield Select(
          [("+ New", postit_store.NEW_KEY)],
          value=postit_store.NEW_KEY,
          allow_blank=False,
          id="postit-request-select",
          classes="postit-request-select",
        )
        yield Button(
          f"{icons.REFRESH}",
          id="postit-reload",
          classes="postit-reload-btn",
          tooltip="Reload postit files",
        )
      with Vertical(classes="postit-request-block"):
        with Horizontal(classes="postit-request-line"):
          yield Select(
            [(m, m) for m in sorted(postit_store.HTTP_METHODS)],
            value="GET",
            allow_blank=False,
            id="postit-method",
            classes="postit-method-select",
          )
        yield Label("URL", classes="postit-url-label")
        yield Input(placeholder="https://…", id="postit-url", classes="postit-url-input")
      with Vertical(classes="postit-editor-stack"):
        with TabbedContent(classes="postit-editor-tabs"):
          with TabPane("Headers", classes="postit-tab-pane postit-tab-headers"):
            yield TextArea(
              "{}",
              id="postit-headers",
              classes="postit-headers-editor",
              language="json",
            )
          with TabPane("Body", classes="postit-tab-pane postit-tab-body"):
            yield TextArea("", id="postit-body", classes="postit-body-editor")
        with Horizontal(classes="postit-actions"):
          yield Button(
            f"{icons.RUN} Send",
            id="postit-send",
            classes="postit-btn postit-send-btn",
          )
          yield Button(
            "Save",
            id="postit-save",
            classes="postit-btn postit-save-btn",
          )
        yield Label("—", id="postit-status", classes="postit-status")
        yield TextArea(
          "",
          id="postit-response",
          classes="postit-response-body",
          read_only=True,
        )

  def on_mount(self) -> None:
    self.reload_collection()

  def reload_collection(self) -> None:
    wd = cfg.get("session.working_directory", ".")
    self._merged = postit_store.load_merged_requests(wd)
    sel = self.query_one("#postit-request-select", Select)
    opts: list[tuple[str, str]] = [("+ New", postit_store.NEW_KEY)]
    for stem in sorted(self._merged.keys()):
      opts.append((stem, stem))
    self._suppress_reload = True
    try:
      cur = sel.value
      sel.set_options(opts)
      if cur in [o[1] for o in opts]:
        sel.value = cur
      else:
        sel.value = postit_store.NEW_KEY
    finally:
      self._suppress_reload = False
    self._apply_request_select_to_fields(only_saved=True)

  def _apply_request_select_to_fields(self, *, only_saved: bool = False) -> None:
    if self._suppress_reload:
      return
    sel = self.query_one("#postit-request-select", Select)
    v = sel.value
    if v is Select.BLANK or str(v) == postit_store.NEW_KEY:
      if only_saved:
        return
      self._apply_new_template()
      return
    self._apply_from_merged(str(v))

  def _apply_new_template(self) -> None:
    self.query_one("#postit-method", Select).value = "GET"
    self.query_one("#postit-url", Input).value = ""
    self.query_one("#postit-headers", TextArea).text = "{}"
    self.query_one("#postit-body", TextArea).text = ""

  def _apply_from_merged(self, stem: str) -> None:
    data = self._merged.get(stem, {})
    norm, err = postit_store.normalize_request(data)
    if err:
      self.app.notify(err, severity="error")
      return
    self.query_one("#postit-method", Select).value = norm["method"]
    self.query_one("#postit-url", Input).value = norm["url"]
    self.query_one("#postit-headers", TextArea).text = json.dumps(
      norm["headers"], indent=2
    )
    self.query_one("#postit-body", TextArea).text = norm["body"]

  def on_select_changed(self, event: Select.Changed) -> None:
    # Ignore method Select; @on(..., "#id") can miss bubbled Select.Changed in some cases.
    if event.control.id != "postit-request-select":
      return
    if self._suppress_reload:
      return
    self._apply_request_select_to_fields()

  @on(Button.Pressed, "#postit-reload")
  def _on_reload(self) -> None:
    self.reload_collection()
    self.app.notify("Postits reloaded.")

  @on(Button.Pressed, "#postit-send")
  def _on_send_pressed(self) -> None:
    self._send_http()

  @on(Button.Pressed, "#postit-save")
  def _on_save_pressed(self) -> None:
    sel = self.query_one("#postit-request-select", Select)
    default = "untitled"
    if sel.value != postit_store.NEW_KEY:
      default = str(sel.value)

    def on_name(result: str | None) -> None:
      if result is None or not str(result).strip():
        return
      stem = postit_store.sanitize_stem(str(result))
      self._persist_postit(stem)

    self.app.push_screen(
      InputModal("Save postit (filename stem)", initial_value=default),
      on_name,
    )

  def _persist_postit(self, stem: str) -> None:
    wd = cfg.get("session.working_directory", ".")
    method = str(self.query_one("#postit-method", Select).value)
    url = self.query_one("#postit-url", Input).value
    headers_t = self.query_one("#postit-headers", TextArea).text
    body = self.query_one("#postit-body", TextArea).text
    req, err = postit_store.request_from_ui_fields(method, url, headers_t, body)
    if err:
      self.app.notify(err, severity="error")
      return
    path, werr = postit_store.write_request(wd, stem, req)
    if werr:
      self.app.notify(werr, severity="error")
      return
    self.app.notify(f"Saved {path}")
    self.reload_collection()
    self._suppress_reload = True
    try:
      self.query_one("#postit-request-select", Select).value = stem
    finally:
      self._suppress_reload = False
    self._apply_from_merged(stem)

  def _show_response(self, status: str, body: str) -> None:
    self.query_one("#postit-status", Label).update(status)
    self.query_one("#postit-response", TextArea).text = body

  @work
  async def _send_http(self) -> None:
    method = str(self.query_one("#postit-method", Select).value)
    url = self.query_one("#postit-url", Input).value
    headers_t = self.query_one("#postit-headers", TextArea).text
    body = self.query_one("#postit-body", TextArea).text
    req, err = postit_store.request_from_ui_fields(method, url, headers_t, body)
    if err:
      self.app.notify(err, severity="error")
      return

    def run() -> tuple[int, str, str, str]:
      resp = postit_store.execute_request(req)
      head_lines = "\n".join(f"{k}: {v}" for k, v in resp.headers.items())
      return (
        resp.status_code,
        resp.reason or "",
        head_lines,
        resp.text,
      )

    try:
      code, reason, head_lines, text = await asyncio.to_thread(run)
    except Exception as e:
      self._show_response(f"Error: {type(e).__name__}", str(e))
      return
    status = f"{code} {reason}".strip()
    combined = f"{head_lines}\n\n{text}"
    self._show_response(status, combined)


def get_sidebar_widget():
  return PostitSidebarTab(classes="postit-root")
