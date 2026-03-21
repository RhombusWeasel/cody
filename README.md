# Cody

A TUI (terminal user interface) AI coding assistant built with [Textual](https://textual.textualize.io/). Chat with LLMs, manage files, run commands, and work with git—all from the terminal.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

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
- Config layers (merge order): `~/.agents/cody_settings.json`, `$CODY_DIR/.agents/cody_config.json`, `{project}/.agents/cody_config.json`. Later paths override earlier ones; saves go to the project path in that list.
- **On disk, settings are only stored encrypted** as `*.json.enc` (PBKDF2-SHA256 + Fernet). If a plaintext `*.json` is found at load, it is read, removed, and written as `.enc` using your password. Saves always write `.enc` and delete any stray plaintext file at the save path. While running, merged settings live in memory as a dict. Scripts (e.g. `run_agent`) need `--config-password-file` or `CODY_CONFIG_PASSWORD` whenever plaintext or encrypted configs exist, or for non-interactive first saves.
- Provider/model selection, API keys, prompts, skill directories

`db.connections` stores sidebar database connections. Each entry may include:

- `path` — DSN or SQLite file path
- `type` — `sqlite3` or `sqlite` today; more drivers can register later
- `label` — optional display name
- `opts` — backend-specific options object
- `auth` — optional authentication (see below)

The Cody project database (chats, agents, todos) uses SQLite under `$CODY_DIR/.agents/cody_data.db`. On disk it is stored as **`cody_data.db.enc`**: the same PBKDF2 + Fernet envelope as config. The key uses your config password and, when any encrypted config layer is loaded, **the same salt and iteration count** as that layer (otherwise a new salt is created and kept alongside the project config save path). At runtime the DB is held in memory (`sqlite3` serialize/deserialize); each write updates the encrypted file. A legacy plaintext `cody_data.db` is migrated on first open (removed after a successful `.enc` write). Other SQLite paths you add in settings stay unencrypted plain files.

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