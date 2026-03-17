# Cody

A TUI (terminal user interface) AI coding assistant built with [Textual](https://textual.textualize.io/). Chat with LLMs, manage files, run commands, and work with git—all from the terminal.

## Features

### Chat
- Multi-tab chat with customizable tooling.
- Slash commands (e.g. `/help`, `/clear`) with autocomplete; project-specific commands from `{project}/.agents/commands/`

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

## Customized Tooling

Both **skills** and **slash commands** use tiered loading: later directories override earlier ones for the same name.

| Layer | Skills | Commands |
|-------|--------|----------|
| Built-in | `$CODY_DIR/skills/` | `$CODY_DIR/components/chat/cmd/` |
| Cody-level | — | `$CODY_DIR/cmd/` |
| User global | `~/.agents/skills/` | `~/.agents/commands/` |
| Project | `{project}/.agents/skills/` | `{project}/.agents/commands/` |

Configure paths via `skills.directories` and `commands.directories` in config.

### Example: custom slash command

Create `my_project/.agents/commands/echo.py`:

```python
from utils.cmd_loader import CommandBase

class EchoCommand(CommandBase):
    description = "Echoes the given text as a system message"

    async def execute(self, app, args: list[str]):
        try:
            from components.chat.chat import MsgBox
            from textual.widgets import TabbedContent

            text = " ".join(args) if args else "(nothing)"
            tabs = app.query_one("#chat_tabs", TabbedContent)
            if not tabs.active:
                return
            pane = tabs.get_pane(tabs.active)
            msg_box = pane.query_one(MsgBox)
            msg_box.messages = [*msg_box.messages, {"role": "system", "content": text}]
        except Exception as e:
            print(f"Echo command failed: {e}")
```

Use `/echo hello world` in chat. One `CommandBase` subclass per file; filename becomes the command name.

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
```