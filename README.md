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

## Documentation

- [Utils reference](docs/utils_reference.md) — what each `utils/` module does and when to use it
- [Extending Cody](docs/extending_cody.md) — skills, tools, commands, themes, tiered paths, and startup order

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
- Custom tools are loaded from tiered `tools/` directories: `$CODY_DIR/tools/`, `~/.agents/tools/`, then `{project}/.agents/tools/` (later overrides earlier). Tools are passed with every call and must contain a valid docstring as they bypass the skills progressive loading system.
Because of this they are discouraged and users should favour the below skills implementation.

### Config
- JSON config: `~/.agents/cody_settings.json` (global) + `{project}/.agents/cody_config.json` (local)
- Provider/model selection, API keys, prompts, skill directories

## Customized Tooling

**tools** and **skills** use tiered loading: later directories override earlier ones for the same name. **Slash commands:** built-in modules live in `$CODY_DIR/cmd/`; each skill can add `cmd/*.py` next to its `SKILL.md` under the same tiered `skills/` trees (`$CODY_DIR/skills/`, `~/.agents/skills/`, `{project}/.agents/skills/`). Later-loaded command dirs override the same command name. Optional extra command dirs: `commands.directories` in config (resolved before skill `cmd/` folders).

| Layer | Skills | Slash commands |
|-------|--------|----------------|
| Built-in | `$CODY_DIR/skills/` | `$CODY_DIR/cmd/` + each `$CODY_DIR/skills/<name>/cmd/` |
| User global | `~/.agents/skills/` | each `~/.agents/skills/<name>/cmd/` |
| Project | `{project}/.agents/skills/` | each `{project}/.agents/skills/<name>/cmd/` |

Configure paths via `skills.directories` and optionally `commands.directories` in config.

### Examples

Check out the `examples/` directory for sample code on how to extend Cody:
- `examples/skills/` - Custom skills (including slash commands under `<skill>/cmd/`)
- `examples/component/` - Custom sidebar UI components

## Keybindings

Open the **leader menu** with `Ctrl+Space` (many terminals send this as `Ctrl+@`; both work by default). Then use single-letter chords; examples:

| Chord | Action |
|-------|--------|
| `b` then `u` | Toggle util sidebar |
| `b` then `t` | Toggle terminal sidebar |
| `i` | Send terminal buffer to chat |
| `w` then `v` / `h` | Split workspace vertical / horizontal |
| `w` then `c` / `n` | Close chat tab / new chat tab |
| `w` then `p` | Close active pane (when split) |
| `w` then `l` / `r` | Focus next / previous pane |

Editor tabs still use `Ctrl+S` to save. Override the leader key with `interface.leader_key` in config.

## Project Structure

```
cody/
├── main.py              # App entry
├── app.css              # Styles
├── cmd/                 # Built-in slash commands (CommandBase)
├── components/          # UI (chat, sidebar, terminal, fs, git, db)
├── tools/               # Built-in tools (skills, system)
├── skills/              # Bundled skills (e.g. coding); optional skill cmd/ per skill
├── utils/               # Agent, config, providers, db, git, etc.
└── config.json_example  # Config template
```