import asyncio
import webbrowser
from collections.abc import Callable
from urllib.parse import urlparse

from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Input, Label

import utils.password_vault as password_vault
from components.utils.buttons import ActionButton, RunButton
from components.utils.form_modal import FormModal
from skills.brave_search.api import (
  BRAVE_SEARCH_VAULT_CREDENTIAL_ID,
  BRAVE_SEARCH_VAULT_LABEL,
  ensure_brave_search_credential_row,
  fetch_brave_web_search,
  get_brave_api_key,
)

sidebar_label = "󰍉"
sidebar_tooltip = "Brave Search"


def _reload_password_vault_tree(app) -> None:
  """Vault sidebar tree does not refresh when credentials are saved elsewhere."""
  app.query_one("#password_vault_tree").reload()


def _truncate(s: str, max_len: int) -> str:
  s = (s or "").strip()
  if len(s) <= max_len:
    return s
  return s[: max_len - 1] + "…"

class BraveSearchSidebarTab(Vertical):
  """Search via Brave API; results open in the system browser."""

  def compose(self) -> ComposeResult:
    with Horizontal(classes="brave-search-header"):
      yield Input(placeholder="Search…", id="brave_query_input")
      yield RunButton(action=self.on_search_clicked, id="brave_run_btn", tooltip="Search")
    yield VerticalScroll(id="brave_results_scroll")

  def on_search_clicked(self) -> None:
    q = self.query_one("#brave_query_input", Input).value.strip()
    if not q:
      self.app.notify("Enter a search query.", severity="warning")
      return
    password_vault.prompt_master_password(
      on_done=lambda ok: self._continue_search_after_vault(ok, q),
    )

  def _continue_search_after_vault(self, ok: bool, query: str) -> None:
    if not ok:
      return
    ensure_brave_search_credential_row()
    _reload_password_vault_tree(self.app)
    if not get_brave_api_key():
      self._open_brave_token_form(then=lambda: self._run_search_work(query))
      return
    self._run_search_work(query)

  def _save_brave_token_to_vault(
    self,
    merged: dict,
    *,
    then: Callable[[], None] | None = None,
  ) -> None:
    tok = (merged.get("token") or "").strip()
    password_vault.upsert_credential(
      BRAVE_SEARCH_VAULT_CREDENTIAL_ID,
      BRAVE_SEARCH_VAULT_LABEL,
      "default",
      "",
      tok,
    )
    _reload_password_vault_tree(self.app)
    self.app.notify(
      f"Saved to vault as '{BRAVE_SEARCH_VAULT_LABEL}' under Credentials → default "
      "(expand the row and use the eye icon to reveal the token).",
      severity="information",
    )
    if then:
      then()

  def _open_brave_token_form(self, *, then: Callable[[], None] | None = None) -> None:
    schema = [
      {
        "key": "token",
        "label": "Brave Search API token",
        "type": "password",
        "required": True,
      },
    ]

    def on_save(merged: dict) -> None:
      self._save_brave_token_to_vault(merged, then=then)

    self.app.push_screen(FormModal("Brave Search API key", schema, callback=on_save))

  @work
  async def _run_search_work(self, query: str) -> None:
    scroll = self.query_one("#brave_results_scroll", VerticalScroll)
    await scroll.remove_children()
    await scroll.mount(Label("Searching…"))

    try:
      results = await asyncio.to_thread(fetch_brave_web_search, query)
    except Exception as e:
      await scroll.remove_children()
      await scroll.mount(Label(f"Error: {e}", classes="brave-search-error"))
      self.app.notify(str(e), severity="error")
      return

    await scroll.remove_children()
    if not results:
      await scroll.mount(Label("No results."))
      return

    for r in results:
      url = r.get("url") or ""
      title = _truncate(r.get("title") or url, 72)
      desc = (r.get("description") or "").strip()
      host = urlparse(url).netloc or url

      await scroll.mount(
        Vertical(
          ActionButton(title, action=lambda u=url: webbrowser.open(u), classes="brave-result-btn"),
          Label(_truncate(desc, 200), classes="brave-result-desc"),
          Label(host, classes="brave-result-host"),
          classes="brave-result-block",
        )
      )


def get_sidebar_widget():
  return BraveSearchSidebarTab()
