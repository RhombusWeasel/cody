"""Sidebar tab for encrypted password vault."""
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Label

from components.sidebar.password_vault_tree import PasswordVaultTree
from components.utils.form_modal import FormModal
import utils.password_vault as password_vault


class PasswordVaultTab(VerticalScroll):
  """Prompts for master password when the tab is activated; lists credentials and notes."""


  def compose(self) -> ComposeResult:
    yield Label(
      "Select this tab to unlock the vault.",
      id="vault_locked_hint",
      classes="vault-hint",
    )
    yield PasswordVaultTree(id="password_vault_tree", host=self)

  def on_mount(self) -> None:
    tree = self.query_one("#password_vault_tree", PasswordVaultTree)
    tree.display = False
    if password_vault.is_unlocked():
      self._show_unlocked()

  def request_unlock_if_needed(self) -> None:
    """Called when the vault tab becomes active (from Sidebar; TabActivated bubbles upward only)."""
    if password_vault.is_unlocked():
      self._show_unlocked()
      return
    password_vault.prompt_master_password(on_done=self._on_unlock_done)

  def _on_unlock_done(self, ok: bool) -> None:
    if ok:
      self._show_unlocked()
    else:
      hint = self.query_one("#vault_locked_hint", Label)
      hint.update("Vault locked. Select this tab again to try again.")

  def _show_unlocked(self) -> None:
    self.query_one("#vault_locked_hint", Label).display = False
    self.query_one("#password_vault_tree", PasswordVaultTree).display = True
    try:
      from skills.brave_search.api import ensure_brave_search_credential_row

      ensure_brave_search_credential_row()
    except ImportError:
      pass
    # Tree's first _refresh ran while locked (empty); reload after unlock from chat or tab.
    self._reload_tree()

  def _reload_tree(self) -> None:
    self.query_one("#password_vault_tree", PasswordVaultTree).reload()

  def open_form_credential(self, entry_id: str | None) -> None:
    schema = [
      {"key": "label", "label": "Label", "type": "text"},
      {"key": "group", "label": "Group", "type": "text", "placeholder": "default"},
      {"key": "username", "label": "Username", "type": "text"},
      {"key": "password", "label": "Password", "type": "password", "required": True},
    ]
    args: dict = {}
    title = "Add credential"
    if entry_id:
      row = password_vault.get_credential_by_id(entry_id)
      if row:
        title = "Edit credential"
        args = {
          "entry_id": entry_id,
          "label": row.get("label") or "",
          "group": row.get("group") or "",
          "username": row.get("username") or "",
          "password": password_vault.decrypt_password(row),
        }

    def on_save(merged: dict) -> None:
      eid = merged.get("entry_id")
      password_vault.upsert_credential(
        eid,
        merged.get("label") or "",
        (merged.get("group") or "").strip() or "default",
        merged.get("username") or "",
        merged.get("password") or "",
      )
      self._reload_tree()

    self.app.push_screen(FormModal(title, schema=schema, args=args or None, callback=on_save))

  def open_form_note(self, entry_id: str | None) -> None:
    schema = [
      {"key": "label", "label": "Label", "type": "text"},
      {"key": "group", "label": "Group", "type": "text", "placeholder": "default"},
      {"key": "body", "label": "Note", "type": "textarea", "required": True},
    ]
    args: dict = {}
    title = "Add secure note"
    if entry_id:
      row = password_vault.get_note_by_id(entry_id)
      if row:
        title = "Edit secure note"
        args = {
          "entry_id": entry_id,
          "label": row.get("label") or "",
          "group": row.get("group") or "",
          "body": password_vault.decrypt_note_body(row),
        }

    def on_save(merged: dict) -> None:
      eid = merged.get("entry_id")
      password_vault.upsert_note(
        eid,
        merged.get("label") or "",
        (merged.get("group") or "").strip() or "default",
        merged.get("body") or "",
      )
      self._reload_tree()

    self.app.push_screen(FormModal(title, schema=schema, args=args or None, callback=on_save))
