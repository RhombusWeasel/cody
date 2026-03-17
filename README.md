# Cody

A TUI (terminal user interface) AI coding assistant built with [Textual](https://textual.textualize.io/). Chat with LLMs, manage files, run commands, and work with git—all from the terminal.

## Features

### Chat
- Multi-tab chat with persistent history (SQLite)
- Ollama and OpenAI provider support
- Tool-calling for skills and system commands
- Send terminal output to chat for context
- Slash commands (e.g. `/help`, `/clear`) with autocomplete
- Input history

### Sidebar
- **Chat history** – Browse and restore past conversations
- **File tree** – Navigate project files
- **Git** – View status, stage/unstage, commit (with AI-generated messages), checkout branches, view diffs
- **Database** – Connect to SQLite DBs, run queries, view results, export CSV
- **Tools** – Enable/disable tools and skill groups
- **Settings** – Provider, model, sidebar visibility, system/tool message display
- **Skill tabs** – Extensible sidebar tabs from skills (e.g. coding skill)

### Terminal
- Integrated terminal (right sidebar)
- Send terminal output to chat with optional question

### Skills
- Pluggable skills from `~/.agents/skills`, `$CODY_DIR/skills`, `{project}/.agents/skills`
- Built-in **file-manipulation** skill: create, read, edit, search files
- Skills expose tools via `activate_skill` and `run_skill`
- Per-skill enable/disable in config

### Tools
- `run_command` – Execute shell commands
- `activate_skill` – Load skill instructions
- `run_skill` – Run skill scripts
- Custom tools from `tools/` and `{project}/.agents/tools/`

### Config
- JSON config: `~/.agents/cody_settings.json` (global) + `{project}/.agents/cody_config.json` (local)
- Provider/model selection, API keys, prompts, skill directories

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

## Keybindings

| Key | Action |
|-----|--------|
| `Ctrl+S` | Toggle sidebar |
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
``