# Cody

A TUI (terminal user interface) AI coding assistant built with [Textual](https://textual.textualize.io/). Chat with LLMs, manage files, run commands, and work with git—all from the terminal.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Dependencies include **`cryptography`** (config + project DB at rest)

## Installation

```bash
git clone <repo>
cd cody
uv sync
```

Copy the config template and edit:

```bash
cp config.json_example .agents/cody_config.json
# Or for global: ~/.agents/cody_settings.json
```

## Usage

```bash
uv run python main.py [working_directory]
```

Defaults to current directory. Working directory is used for file tree, git, and skills.

Optional flags:

- `--encrypt-config` — encrypt any remaining plaintext JSON at the paths below (prompts for a **new** password), then exits. Normal startup already migrates plaintext → `.enc` on load when you enter your existing password.
- `--config-password-file PATH` — read the config password from a file (for non-interactive runs). If any plaintext `.json` or `.json.enc` exists at those paths, a password is required at startup (or set `CODY_CONFIG_PASSWORD`; note it may be visible in `ps` on some systems). The first time you save with no config files yet, you are prompted (or use the env var).

## Features

### Skills
Fully compliant with the anthropic skill specification allowing for tiered loading of configuration and skillsets.
Pluggable skills from 
  - `$CODY_DIR/skills`
  - `~/.agents/skills`
  - `{project}/.agents/skills`


### Tools
We only pass 3 tools to the agent by default
- `run_command` – Execute shell commands
- `activate_skill` – Load skill instructions
- `run_skill` – Run skill scripts
- Custom tools are loaded from `$CODY_DIR/tools/` and `{project}/.agents/tools/` Tools are passed with every call and must contain a valid docstring as they bypass the skills progressive loading system.
Because of this they are discouraged and users should favour the below skills implementation.

### Config
- Config layers (merge order): `~/.agents/cody_settings.json`, `$CODY_DIR/.agents/cody_config.json`, `{project}/.agents/cody_config.json`. Later paths override earlier ones; saves go to the project path in that list. On disk these are stored as **`*.json.enc`** once migrated (see **Encryption at rest** below).
- Provider/model selection, API keys, prompts, skill directories

### Encryption at rest

Cody uses the Python **`cryptography`** package: **PBKDF2-HMAC-SHA256** derives a key from your password; **Fernet** encrypts the payload (authenticated encryption). You use one **config password** for both settings and the built-in project database (unless noted below).

**Configuration (`*.json.enc`)**

- Plaintext `*.json` at a config path is loaded once, deleted, and replaced with `*.json.enc` after you enter the password. New saves only write `.enc` and remove any stray plaintext at the save path.
- While the app runs, merged settings live in memory as a normal dict.

**Project database (`cody_data.db.enc`)**

- Chats, agents, todos, and input history use SQLite. The logical path is still **`$CODY_DIR/.agents/cody_data.db`** (what you see in the UI and in `db.connections` for “Cody Data”).
- **On disk** the file is **`cody_data.db.enc`**: same binary envelope as config (not SQLCipher). The key uses the **same password** as config; when an encrypted config layer is already loaded, the DB reuses that layer’s **salt and iteration count** when possible (otherwise a salt is created and tied to the project config save path).
- At runtime the DB image is loaded with **`sqlite3` `deserialize`** into memory; after each query the DB is **serialized** and written back to `.enc` (with a temp file + replace).
- A legacy plaintext **`cody_data.db`** is migrated on first open: encrypted to `.enc`, then the plain file is removed.
- **Other** SQLite databases you add under `db.connections` are still ordinary **unencrypted** files on disk.

**Passwords for scripts and automation**

- Set `CODY_CONFIG_PASSWORD` or pass `--config-password-file` when any encrypted config or the project DB already exists, or for non-interactive first saves. The value may be visible in `ps` on some systems.

`db.connections` stores sidebar database connections. Each entry may include:

- `path` — DSN or SQLite file path
- `type` — `sqlite3` or `sqlite` today; more drivers can register later
- `label` — optional display name
- `opts` — backend-specific options object
- `auth` — optional authentication (see below)

**Database `auth` object** (optional, per connection):

- `method`: `none`, `dsn` (credentials only in URL; no extra fields), `password`, or `token`
- **Password mode:** `username`, `password`, or indirect `username_env` / `password_env` (environment variable *names*), or `username_cfg` / `password_cfg` (dot paths passed to `cfg.get`, e.g. `db.secrets.pg_password`)
- **Token mode:** `token`, or `token_env` / `token_cfg` (same pattern)
- **SSL:** optional nested `ssl`: `{ "mode": "require", "rootcert": "...", "cert": "...", "key": "..." }` — merged into backend opts as `sslmode`, `sslrootcert`, `sslcert`, `sslkey`

Resolution order for each secret: inline value first (after interpolation), then named env var, then cfg path. Inline strings support **`expand_config_value`** from `utils.cfg_man`: `${env:VAR}` and `${cfg:dot.path}` in any string field.

Put long-lived secrets in `db.secrets` (or another key) in the same JSON and reference them with `password_cfg` / `${cfg:...}` so you can tighten file permissions on the config file. Prefer env vars in production.

## Customized Tooling

**tools**, **skills** and **slash commands** use tiered loading: later directories override earlier ones for the same name.

| Layer | Skills | Commands |
|-------|--------|----------|
| Built-in | `$CODY_DIR/skills/` | `$CODY_DIR/components/chat/cmd/` |
| Cody-level | — | `$CODY_DIR/cmd/` |
| User global | `~/.agents/skills/` | `~/.agents/commands/` |
| Project | `{project}/.agents/skills/` | `{project}/.agents/commands/` |

Configure paths via `skills.directories` and `commands.directories` in config.

### Examples

Check out the `examples/` directory for sample code on how to extend Cody:
- `examples/command/` - Custom slash commands
- `examples/skills/` - Custom skills
- `examples/component/` - Custom sidebar UI components

## Keybindings

| Key | Action |
|-----|--------|
| ``Ctrl+` `` | Toggle sidebar |
| `Ctrl+T` | Toggle terminal |
| `Ctrl+N` | New chat tab |
| `Ctrl+W` | Close chat tab |

## Project Structure

```
cody/
├── main.py              # App entry
├── app.css              # Styles
├── components/          # UI (chat, sidebar, terminal, fs, git, db)
├── tools/               # Built-in tools (skills, system)
├── skills/              # Bundled skills (e.g. coding)
├── utils/               # Agent, config, providers, db, git, etc.
└── config.json_example  # Config template
```