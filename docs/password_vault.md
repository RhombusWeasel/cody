# Password vault (consumers)

How to **store** and **read** secrets with the **public** API in [`utils/password_vault.py`](../utils/password_vault.py). Cody core (sidebar, providers) may use additional module-level helpers; see [`utils_reference.md`](utils_reference.md).

**Storage:** `~/.agents/cody_passwords_db.enc` — JSON on disk; secrets are encrypted (Fernet with a key derived from the user’s master password).

## TUI registration

Call **`init_vault(app)`** from the running Textual app on mount and **`init_vault(None)`** on shutdown ([`main.py`](../main.py)). Async getters use this to show the master-password modal when the vault is locked. Outside the TUI, `init_vault` is never set (or cleared), so async getters cannot unlock and behave like “vault locked.”

## Public API

Only these names are the supported extension surface (see `__all__` in the module):

| Function | Notes |
|----------|--------|
| **`init_vault(app \| None)`** | Register or clear the Textual app. |
| **`register_credential(credential_name, group, default_username, default_password)`** | Upsert a credential. **`credential_name`** is the stable row **`id`** (e.g. `cody_skill_brave_search_api_key`). On first insert, **`label`** in the vault UI is set to that string; on update, the existing **`label`** is preserved so users can rename the row in the sidebar. Requires an **unlocked** vault; raises `RuntimeError("Vault is locked")` otherwise. Persists immediately. |
| **`register_secure_note(secure_note_name, group, data)`** | Same pattern for secure notes (`id` = `secure_note_name`). |
| **`async get_credential(credential_name)`** | Returns **`{"username": str, "password": str}`** (values stripped). If locked and the app is registered, **awaits** the unlock modal. If unlock fails or there is no app, returns empty strings. Missing row or bad cipher → empty strings. |
| **`async get_secure_note(secure_note_name)`** | Returns decrypted note body as **`str`**, or **`""`** with the same lock/missing rules as **`get_credential`**. |

## Sync reads when already unlocked

In-process code that **cannot** `await` (e.g. sync provider resolution) should only read the vault when **`is_unlocked()`** is true. The module still exposes **`get_secret(entry_id)`** and **`get_credential_username(entry_id)`** for that pattern; they return **`""`** if locked and do not open UI. Prefer **`await get_credential(id)`** in async TUI flows so the user can unlock first.

## Master password without async

- **`try_unlock(password: str) -> bool`** — when you already have the master password string (e.g. tests). Creates the vault file if none exists.
- **`prompt_master_password(on_done=..., app=None)`** — modal unlock; uses **`init_vault`**’s app when **`app`** is omitted. If several callers run while the vault is still locked (e.g. multiple sidebars on startup), they share **one** unlock modal; every **`on_done`** runs with the same success or failure when that modal completes.

## Session clear hooks

Extensions that cache decrypted material should register **`register_vault_session_clear_hook(fn)`** so locking the vault clears those caches (see [`utils_reference.md`](utils_reference.md)).
