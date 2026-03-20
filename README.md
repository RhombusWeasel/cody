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
- JSON config: `~/.agents/cody_settings.json` (global) + `{project}/.agents/cody_config.json` (local)
- Provider/model selection, API keys, prompts, skill directories

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