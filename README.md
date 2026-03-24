# Cody

A TUI (terminal user interface) AI coding assistant built with [Textual](https://textual.textualize.io/). Chat with LLMs, manage files, run commands, and work with git—all from the terminal.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

## Installation

```bash
git clone https://github.com/RhombusWeasel/cody
cd cody
uv sync
```

On first run, Cody merges built-in defaults with any JSON you already have under `~/.agents/cody_settings.json` and `{project}/.agents/cody_config.json`, then writes missing keys. Project files store **only overrides** relative to global (and the app repo’s bundled `.agents/cody_config.json` if present).

## Usage

```bash
uv run python main.py [working_directory]
```

