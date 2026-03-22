# Password vault (developer guide)

How to register, read, and update secrets using [`utils/password_vault.py`](../utils/password_vault.py). For a short API summary, see [`utils_reference.md`](utils_reference.md). Broader extension context: [extending_cody.md](extending_cody.md).

**On-disk file:** `~/.agents/cody_passwords_db.enc` (JSON with Fernet-encrypted fields).

## Lock state

- **`is_unlocked()`** — session has the derived key and decrypted metadata in memory; all read/write helpers below require this (otherwise `list_*` returns `[]`, `upsert_*` / `delete_*` raise `RuntimeError("Vault is locked")`).
- **`is_file_present()`** — vault file exists (first successful unlock may create it).
- **`clear_session_key()`** — drop the in-memory vault session (and, in core today, clear related caches such as the OpenAI key cache). Call when implementing “lock vault” in the UI. Extensions can register extra clears with **`register_vault_session_clear_hook(fn)`** (no-arg callable; errors swallowed per hook).

## 1. Unlock the vault

- **`try_unlock(password: str) -> bool`** — supply the master password; creates a new vault file if none exists; returns `False` on wrong password or bad file. Use when you already have the password string (e.g. tests, migration tools). **Do not** use this to bypass the user for the master password in the TUI.
- **`prompt_master_password(app, on_done=callable)`** — the supported way in the Textual app to ask for the **master** password: pushes [`InputModal`](../components/utils/input_modal.py) (password mode), calls `try_unlock`, then `on_done(True)` if unlocked. If already unlocked, calls `on_done(True)` immediately. From **async** code that must `await` completion, wrap with `asyncio.Future` + `app.call_later` (see [Slash commands: preview then add to chat](extending_cody.md#slash-commands-preview-then-add-to-chat) in *Extending Cody* and `_await_modal` in [`openai_vault.py`](../utils/providers/openai_vault.py)).

## 2. Register or update a credential (secret string)

Credentials are rows with `id`, `label`, `group`, `username`, and an encrypted password.

1. Ensure the vault is unlocked (step 1).
2. Choose a **stable string `id`** (e.g. `cody_provider_openai_api_key`) if your feature needs to find the same row again from code and show it under a known label in the Vault sidebar. To always create a new row, pass **`entry_id=None`**; a UUID is generated.
3. Call **`upsert_credential(entry_id, label, group, username, password_plain)`**.  
   - `group` defaults in storage to `"default"` if empty.  
   - `password_plain` may be `""` (still stored encrypted).  
   - Persists to disk inside the function.

## 3. Read a credential

1. Ensure the vault is unlocked.
2. **`row = get_credential_by_id(entry_id)`** — returns a dict with `id`, `label`, `group`, `username`, `password_cipher` (ciphertext only; do not log the row).
3. **`decrypt_password(row) -> str`** — plaintext secret. If `row` is `None` or cipher missing, you get `""`.

For browsing: **`list_credentials()`** returns copies of rows (still ciphertext in `password_cipher`); decrypt only the rows you need.

## 4. Secure notes

Same pattern with **`upsert_note(entry_id, label, group, body_plain)`**, **`get_note_by_id`**, **`list_notes`**, **`decrypt_note_body(row)`**, **`delete_note(entry_id)`**.

## 5. Delete

- **`delete_credential(entry_id)`**, **`delete_note(entry_id)`** — require unlocked vault; persist immediately.

## Process and threading

- Unlock state is **global to the running Python process**. A background worker thread may call `decrypt_*` / `list_*` **after** the vault is unlocked in that same process.
- A **separate process** (e.g. `python skills/agents/scripts/run_agent.py`) does not share the session; it cannot see an unlocked vault from the TUI.

## Using a vault secret before threaded / non-UI work

If the consumer runs under **`asyncio.to_thread`** or otherwise has no `app`, you must **finish** master-password and any “enter secret” modals on the **main/async** Textual side first, then pass the result via an in-memory cache or closure, then start the thread. See **`ensure_openai_api_key_for_tui`** in [`utils/providers/openai_vault.py`](../utils/providers/openai_vault.py) and the **`await` before `to_thread`** in [`components/chat/chat.py`](../components/chat/chat.py) `MsgBox.get_agent_response`.

## Reference: OpenAI + config fallback

- Fixed credential id and TUI preflight: [`openai_vault.py`](../utils/providers/openai_vault.py). Provider read path: [`openai.py`](../utils/providers/openai.py) (cache, then non-placeholder `providers.openai.api_key`, then env via `OpenAI()`).
- **`looks_like_placeholder_openai_api_key`** — template strings in config (e.g. containing `nice-try-byok`) are not treated as real keys so the vault flow still runs.
- **CLI `TaskAgent` / `run_agent.py`** — no `app`; vault modals are not available; use config / environment.

## Reference: Memory (Reverie) skill

- Credential id **`cody_skill_memory_password`** (label “Memory service”): username + password for **POST /login** on the Reverie-style memory API. With the vault unlocked in the app, that row is used when present; otherwise use `memory.username` / `memory.password` in config or **`CODY_MEMORY_PASSWORD`** (and **`CODY_MEMORY_USERNAME`** if you inject username via env). Skill scripts invoked via **`run_skill`** run in a **subprocess** (§Process and threading) without an in-process vault session. When the vault is **unlocked in the Cody process**, **`run_skill`** copies this row into **`CODY_MEMORY_USERNAME`** / **`CODY_MEMORY_PASSWORD`** in the child environment so memory scripts work from chat without **`CODY_VAULT_MASTER_PASSWORD`**. Otherwise they call **`try_unlock_vault_for_subprocess()`** (from [`skills/memory/components/memory_vault.py`](../skills/memory/components/memory_vault.py)) after loading config so the vault file can be opened when **`CODY_VAULT_MASTER_PASSWORD`** is set (same sensitivity as putting secrets in the environment—avoid on shared machines), or when stdin is a TTY and the user is prompted for the master password. If the vault file is absent or unlock is skipped, config / env still apply.

## Vault sidebar

Users can add, edit, and delete entries in [`components/sidebar/password_vault_tab.py`](../components/sidebar/password_vault_tab.py). Rows created from code with a stable `id` appear there like any other entry; the tab reloads the tree when the unlocked view is shown so data added from chat flows stays visible.
