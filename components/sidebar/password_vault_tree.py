"""Vault tree: Credentials / Secure notes branches, groups, secret rows."""
from typing import Any

from textual.widgets import Button

from components.tree.generic_tree import GenericTree
from components.tree.vault_tree_row import VaultSecretLineRow
from components.utils.buttons import ActionButton, AddButton, EditButton
from utils import icons
from utils.tree_model import TreeEntry
import utils.password_vault as password_vault


CRED_ROOT = ("vault", "cred_root")
NOTE_ROOT = ("vault", "note_root")

VAULT_ICON_SET = {
  **icons.DEFAULT_ICON_SET,
  "vault_cred": icons.DB,
  "vault_note": icons.FILE,
}


class PasswordVaultTree(GenericTree):
  """Credentials and secure notes with encrypted fields on disk."""


  def __init__(self, host: Any, **kwargs):
    super().__init__(root_node_id=None, icon_set=VAULT_ICON_SET, **kwargs)
    self._host = host
    self._reveal_ids: set[Any] = set()

  def create_row_widget(self, entry: TreeEntry):
    if entry.row_variant == "vault_secret_line":
      return VaultSecretLineRow(
        indent=entry.indent,
        secret_value=entry.vault_secret,
        revealed=entry.vault_revealed,
        is_note=entry.vault_is_note,
      )
    return super().create_row_widget(entry)

  def get_visible_entries(self) -> list[TreeEntry]:
    if not password_vault.is_unlocked():
      return []

    creds = password_vault.list_credentials()
    notes = password_vault.list_notes()
    result: list[TreeEntry] = []

    result.append(TreeEntry(
      node_id=CRED_ROOT,
      indent="",
      is_expandable=True,
      is_expanded=CRED_ROOT in self._expanded,
      display_name="Credentials",
      icon=self.icon("vault_cred"),
    ))

    if CRED_ROOT in self._expanded:
      groups_cred = sorted({(c.get("group") or "default") for c in creds})
      for i, group_name in enumerate(groups_cred):
        is_last_g = i == len(groups_cred) - 1
        gid = ("vault", "cred_g", group_name)
        g_branch = self.LAST_BRANCH if is_last_g else self.BRANCH
        result.append(TreeEntry(
          node_id=gid,
          indent=g_branch,
          is_expandable=True,
          is_expanded=gid in self._expanded,
          display_name=group_name,
          icon=self.icon("folder"),
        ))
        if gid in self._expanded:
          g_ext = self.SPACER if is_last_g else self.VERTICAL
          in_group = sorted(
            [c for c in creds if (c.get("group") or "default") == group_name],
            key=lambda x: (x.get("label") or "").lower(),
          )
          for j, c in enumerate(in_group):
            is_last_c = j == len(in_group) - 1
            c_branch = self.LAST_BRANCH if is_last_c else self.BRANCH
            nid = ("vault", "cred", c["id"])
            user = c.get("username") or ""
            label = c.get("label") or "(no label)"
            title = f"{label}  ({user})" if user else label
            secret = password_vault.decrypt_password(c)
            result.append(TreeEntry(
              node_id=nid,
              indent=g_ext + c_branch,
              is_expandable=True,
              is_expanded=nid in self._expanded,
              display_name=title,
              icon=self.icon("file"),
            ))
            if nid in self._expanded:
              cont_ext = self.SPACER if is_last_c else self.VERTICAL
              secret_indent = g_ext + cont_ext + self.LAST_BRANCH
              result.append(TreeEntry(
                node_id=("vault", "cred_secret", c["id"]),
                indent=secret_indent,
                is_expandable=False,
                is_expanded=False,
                display_name="",
                icon="",
                row_variant="vault_secret_line",
                vault_secret=secret,
                vault_revealed=nid in self._reveal_ids,
                vault_is_note=False,
              ))

    result.append(TreeEntry(
      node_id=NOTE_ROOT,
      indent="",
      is_expandable=True,
      is_expanded=NOTE_ROOT in self._expanded,
      display_name="Secure notes",
      icon=self.icon("vault_note"),
    ))

    if NOTE_ROOT in self._expanded:
      groups_note = sorted({(n.get("group") or "default") for n in notes})
      for i, group_name in enumerate(groups_note):
        is_last_g = i == len(groups_note) - 1
        gid = ("vault", "note_g", group_name)
        g_branch = self.LAST_BRANCH if is_last_g else self.BRANCH
        result.append(TreeEntry(
          node_id=gid,
          indent=g_branch,
          is_expandable=True,
          is_expanded=gid in self._expanded,
          display_name=group_name,
          icon=self.icon("folder"),
        ))
        if gid in self._expanded:
          g_ext = self.SPACER if is_last_g else self.VERTICAL
          in_group = sorted(
            [n for n in notes if (n.get("group") or "default") == group_name],
            key=lambda x: (x.get("label") or "").lower(),
          )
          for j, n in enumerate(in_group):
            is_last_c = j == len(in_group) - 1
            c_branch = self.LAST_BRANCH if is_last_c else self.BRANCH
            nid = ("vault", "note", n["id"])
            label = n.get("label") or "(no label)"
            secret = password_vault.decrypt_note_body(n)
            result.append(TreeEntry(
              node_id=nid,
              indent=g_ext + c_branch,
              is_expandable=True,
              is_expanded=nid in self._expanded,
              display_name=label,
              icon=self.icon("file"),
            ))
            if nid in self._expanded:
              cont_ext = self.SPACER if is_last_c else self.VERTICAL
              secret_indent = g_ext + cont_ext + self.LAST_BRANCH
              result.append(TreeEntry(
                node_id=("vault", "note_secret", n["id"]),
                indent=secret_indent,
                is_expandable=False,
                is_expanded=False,
                display_name="",
                icon="",
                row_variant="vault_secret_line",
                vault_secret=secret,
                vault_revealed=nid in self._reveal_ids,
                vault_is_note=True,
              ))

    return result

  def get_node_buttons(self, node_id: Any, is_expandable: bool) -> list[Button]:
    if isinstance(node_id, tuple) and len(node_id) == 3 and node_id[1] in ("cred_secret", "note_secret"):
      return []
    if node_id == CRED_ROOT:
      return [
        AddButton(
          action=lambda: self.on_button_action(CRED_ROOT, "add_cred"),
          tooltip="Add credential",
          classes="action-btn icon-btn",
        ),
      ]
    if node_id == NOTE_ROOT:
      return [
        AddButton(
          action=lambda: self.on_button_action(NOTE_ROOT, "add_note"),
          tooltip="Add note",
          classes="action-btn icon-btn",
        ),
      ]
    if isinstance(node_id, tuple) and len(node_id) == 3 and node_id[1] == "cred":
      revealed = node_id in self._reveal_ids
      eye_lbl = icons.EYE_OFF if revealed else icons.EYE
      tip = "Hide secret" if revealed else "Show secret"
      return [
        EditButton(
          action=lambda n=node_id: self.on_button_action(n, "edit"),
          classes="action-btn icon-btn",
        ),
        ActionButton(
          eye_lbl,
          action=lambda n=node_id: self.on_button_action(n, "toggle_reveal"),
          tooltip=tip,
          classes="action-btn icon-btn",
        ),
        ActionButton(
          icons.COPY_CLIPBOARD,
          action=lambda n=node_id: self.on_button_action(n, "copy"),
          tooltip="Copy password",
          classes="action-btn icon-btn",
        ),
      ]
    if isinstance(node_id, tuple) and len(node_id) == 3 and node_id[1] == "note":
      revealed = node_id in self._reveal_ids
      eye_lbl = icons.EYE_OFF if revealed else icons.EYE
      tip = "Hide note" if revealed else "Show note"
      return [
        EditButton(
          action=lambda n=node_id: self.on_button_action(n, "edit"),
          classes="action-btn icon-btn",
        ),
        ActionButton(
          eye_lbl,
          action=lambda n=node_id: self.on_button_action(n, "toggle_reveal"),
          tooltip=tip,
          classes="action-btn icon-btn",
        ),
        ActionButton(
          icons.COPY_CLIPBOARD,
          action=lambda n=node_id: self.on_button_action(n, "copy"),
          tooltip="Copy note",
          classes="action-btn icon-btn",
        ),
      ]
    return []

  def on_button_action(self, node_id: Any, action: str) -> None:
    if action == "add_cred":
      self._host.open_form_credential(None)
      return
    if action == "add_note":
      self._host.open_form_note(None)
      return
    if action == "toggle_reveal":
      if node_id in self._reveal_ids:
        self._reveal_ids.discard(node_id)
      else:
        self._reveal_ids.add(node_id)
      self.reload()
      return
    if action == "copy":
      if isinstance(node_id, tuple) and len(node_id) == 3:
        _, kind, eid = node_id
        if kind == "cred":
          row = password_vault.get_credential_by_id(eid)
          text = password_vault.decrypt_password(row) if row else ""
        else:
          row = password_vault.get_note_by_id(eid)
          text = password_vault.decrypt_note_body(row) if row else ""
        if text:
          self.app.copy_to_clipboard(text)
          self.app.notify("Copied to clipboard.", severity="information")
        return
    if action == "edit":
      if isinstance(node_id, tuple) and len(node_id) == 3:
        _, kind, eid = node_id
        if kind == "cred":
          self._host.open_form_credential(eid)
        else:
          self._host.open_form_note(eid)
