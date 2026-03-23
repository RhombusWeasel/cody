# Password vault (developer guide)

How to register, read, and update secrets using [`utils/password_vault.py`](../utils/password_vault.py). For a short API summary, see [`utils_reference.md`](utils_reference.md). Broader extension context: [extending_cody.md](extending_cody.md).

**On-disk file:** `~/.agents/cody_passwords_db.enc` (JSON with Fernet-encrypted fields).

## Public API (extensions)

The module **`__all__`** lists the supported extension surface:

- **`init_vault(app | None)`** — the TUI registers the running app on mount and clears it on shutdown ([`main.py`](../main.py) `TuiApp.on_mount` / `cleanup`). Used by async getters to show the master-password modal when the vault is locked.
- **`register_credential(credential_name, group, default_username, default_password)`** — upsert by stable row **`id`** (`credential_name`). On first insert, **`label`** in the UI equals `credential_name`; on update, the existing **`label`** is preserved.
- **`register_secure_note(secure_note_name, group, data)`** — same for notes.
- **`async get_credential(credential_name)`** — returns **`{"username": str, "password": str}`**; awaits unlock via modal when needed (requires **`init_vault`**).
- **`async get_secure_note(secure_note_name)`** — decrypted body; same unlock behavior.

## Lock state (module internals)

- **`is_unlocked()`** — session has the derived key and decrypted metadata in memory; **`register_*`** and **`upsert_*`** require this (otherwise **`register_*`** / **`upsert_*`** / **`delete_*`** raise `RuntimeError("Vault is locked")`).
- **`is_file_present()`** — vault file exists (first successful unlock may create it).
- **`clear_session_key()`** — drop the in-memory vault session (and, in core today, clear related caches such as the OpenAI key cache). Call when implementing “lock vault” in the UI. Extensions can register extra clears with **`register_vault_session_clear_hook(fn)`** (no-arg callable; errors swallowed per hook).

## 1. Unlock the vault

- **`try_unlock(password: str) -> bool`** — supply the master password; creates a new vault file if none exists; returns `False` on wrong password or bad file. Use when you already have the password string (e.g. tests, migration tools). **Do not** use this to bypass the user for the master password in the TUI.
- **`prompt_master_password(on_done=callable, app=None)`** — ask for the **master** password: pushes [`InputModal`](../components/utils/input_modal.py) (password mode), calls `try_unlock`, then `on_done(True)` if unlocked. If already unlocked, calls `on_done(True)` immediately. Omit **`app`** when the TUI has called **`init_vault`** (typical). You may still pass **`app`** explicitly. For async code, prefer **`await get_credential(...)`** (which awaits unlock when needed) instead of hand-rolling `asyncio.Future` + `app.call_later` unless you need a custom flow (see **`ensure_openai_api_key_for_tui`** in [`openai_vault.py`](../utils/providers/openai_vault.py)).

## 2. Register or update a credential (extension API)

1. Ensure the vault is unlocked (or use async **`get_credential`** first so the user can unlock).
2. Choose a **stable string id** as **`credential_name`** (e.g. `cody_provider_openai_api_key`).
3. Call **`register_credential(credential_name, group, username, password_plain)`** — persists immediately.

Cody core and the vault sidebar may still use **`upsert_credential(entry_id, label, group, username, password_plain)`** when a distinct UI **`label`** is required on first insert (e.g. Brave Search sidebar).

## 3. Read a credential

### Async (TUI-friendly)

- **`await get_credential(credential_name)`** — username + decrypted password; awaits master-password modal if locked and **`init_vault`** is set.

### Sync (already unlocked)

- **`get_secret(entry_id) -> str`** — decrypted password, **stripped**, or **`""`** if locked / missing / bad cipher. Use when you cannot `await` and the vault is already unlocked (e.g. **`OpenAIProvider.chat`** resolution).
- **`get_credential_username(entry_id) -> str`** — username field, same lock rules.

### Advanced / UI (ciphertext rows)

1. Ensure the vault is unlocked.
2. **`row = get_credential_by_id(entry_id)`** — dict with `id`, `label`, `group`, `username`, `password_cipher`.
3. **`decrypt_password(row) -> str`** — plaintext secret.

For browsing: **`list_credentials()`** returns copies of rows (ciphertext in `password_cipher`).

## 4. Secure notes

**Extension:** **`register_secure_note`**, **`await get_secure_note`**.

**Core / UI:** **`upsert_note(entry_id, label, group, body_plain)`**, **`get_note_by_id`**, **`list_notes`**, **`decrypt_note_body(row)`**, **`delete_note(entry_id)`**.

## 5. Delete

- **`delete_credential(entry_id)`**, **`delete_note(entry_id)`** — require unlocked vault; persist immediately.

## Process and threading

- Unlock state is **global to the running Python process**. A background worker thread may call `decrypt_*` / `list_*` **after** the vault is unlocked in that same process.
- A **separate process** (e.g. `python skills/agents/scripts/run_agent.py`) does not share the session; it cannot see an unlocked vault from the TUI.

## Using a vault secret before threaded / non-UI work

If the consumer runs under **`asyncio.to_thread`** or otherwise has no `app`, you must **finish** master-password and any “enter secret” modals on the **main/async** Textual side first, then pass the result via an in-memory cache or closure, then start the thread. See **`ensure_openai_api_key_for_tui`** in [`utils/providers/openai_vault.py`](../utils/providers/openai_vault.py) and the **`await` before `to_thread`** in [`components/chat/chat.py`](../components/chat/chat.py) `MsgBox.get_agent_response`.

## Reference: OpenAI + config fallback

- Fixed credential id and TUI preflight: [`openai_vault.py`](../utils/providers/openai_vault.py). Provider read path: [`openai.py`](../utils/providers/openai.py) (in-process cache, then non-placeholder `providers.openai.api_key`, then **`get_secret`** for the OpenAI vault id when the vault is unlocked in-process, then env via `OpenAI()`).
- **`looks_like_placeholder_openai_api_key`** — template strings in config (e.g. containing `nice-try-byok`) are not treated as real keys so the vault flow still runs.
- **CLI `TaskAgent` / `run_agent.py`** — no `app`; vault modals are not available; use config / environment.

## Reference: Memory (Reverie) skill

- Credential id **`cody_skill_memory_password`** (label “Memory service”): username + password for **POST /login** on the Reverie-style memory API. With the vault unlocked in the app, that row is used when present; otherwise use `memory.username` / `memory.password` in config or **`CODY_MEMORY_PASSWORD`** (and **`CODY_MEMORY_USERNAME`** if you inject username via env). Skill scripts invoked via **`run_skill`** run in a **subprocess** (§Process and threading) without an in-process vault session. When the vault is **unlocked in the Cody process**, **`run_skill`** copies this row into **`CODY_MEMORY_USERNAME`** / **`CODY_MEMORY_PASSWORD`** in the child environment so memory scripts work from chat without **`CODY_VAULT_MASTER_PASSWORD`**. Otherwise they call **`try_unlock_vault_for_subprocess()`** (from [`skills/memory/components/memory_vault.py`](../skills/memory/components/memory_vault.py)) after loading config so the vault file can be opened when **`CODY_VAULT_MASTER_PASSWORD`** is set (same sensitivity as putting secrets in the environment—avoid on shared machines), or when stdin is a TTY and the user is prompted for the master password. If the vault file is absent or unlock is skipped, config / env still apply.

## Vault sidebar

Users can add, edit, and delete entries in [`components/sidebar/password_vault_tab.py`](../components/sidebar/password_vault_tab.py). Rows created from code with a stable `id` appear there like any other entry; the tab reloads the tree when the unlocked view is shown so data added from chat flows stays visible.
