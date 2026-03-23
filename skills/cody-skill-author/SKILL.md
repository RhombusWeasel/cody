---
name: cody-skill-author
description: Guides creation of full-stack Cody skills (SKILL.md, scripts, slash commands, LLM tools, sidebar, leader menu, CSS, themes, bundled agents). Use activate_skill first, then read reference/*.md for complete contracts.
---

# Cody skill authoring

When the user wants a **new Cody skill** or extension surface, **`activate_skill("cody-skill-author")` first** so you get this body plus `<skill_resources>` paths. For full detail, **read the markdown under `reference/`** in this skill directory (`extending_cody.md`, `utils_reference.md`, `password_vault.md`). See `reference/README.md` for how to resolve `../` links to repo files.

## Where to place the skill

| User goal | Directory (under …) | Notes |
|-----------|---------------------|--------|
| Ship with Cody / fork | `$CODY_DIR/skills/<folder>/` | Same tier as bundled skills; PR or local install. |
| Personal, all projects | `~/.agents/skills/<folder>/` | Overrides bundled when same skill `name` in frontmatter (later tier wins). |
| One repository only | `{working_directory}/.agents/skills/<folder>/` | Best default when scaffolding from a project chat. |

Skill folder name (directory) can differ from YAML `name` in `SKILL.md`; the **frontmatter `name`** is what appears in the catalog and in `run_skill` / `activate_skill`.

## Skill configuration

Cody merges **global** `~/.agents/cody_settings.json`, optional **repo** `$CODY_DIR/.agents/cody_config.json`, then **project** `{working_directory}/.agents/cody_config.json` (project is the save target and stores **overrides only** vs layers below it). See **`reference/extending_cody.md`** (“Config files”) and **`utils/cfg_man.py`**.

**Defaults (new keys and shapes):** call **`register_default_config({...})`** at import time in a Python module that loads **before** **`cfg.apply_registered_defaults()`** runs. In practice that means something under **`utils/`** (or another package) imported from **`main.py`** alongside `utils.skills`, `utils.agent`, etc. Registered fragments are merged with **`deep_merge_missing`**: existing keys from JSON are never overwritten by defaults. The first successful merge may **persist** missing defaults into the project `cody_config.json` via **`cfg.save()`**.

**Not supported:** a `config.json` next to `SKILL.md` is ignored — do not document or rely on it.

**User overrides:** authors document dotted paths (e.g. `my_skill.api_base`, `my_skill.timeout_seconds`). Users set those in global or project JSON. A skill that ships **only** as a folder (no `utils/` hook) can still define **documented** keys for users to paste into JSON; without `register_default_config`, there are no automatic defaults until something in startup-imported code registers them.

**Enable / disable:** optional map **`skills.enabled`** in JSON: keys are the skill’s frontmatter **`name`**, values are booleans (`false` skips discovery for that skill).

**Reading at runtime:** in **`cmd/`**, **`tools/`**, **`components/`**, or **`scripts/`** (subprocess is separate), use **`from utils.cfg_man import cfg`** and **`cfg.get("dotted.path", default)`**. Skill **`tools/`** and **`cmd/`** load **after** config init — use them to **read** config, not to register defaults.

## Authoring checklist

- **`SKILL.md`**: YAML frontmatter with **`name`** and **`description`** (both required or the skill is skipped).
- **Configuration:** see **Skill configuration** above and **`reference/extending_cody.md`** (“Config files”).
- **`scripts/`**: invoked only via **`run_skill`**; document each script in the SKILL body with example JSON.
- **`tools/*.py`**: at import time call **`register_tool(...)`**; docstring shapes the LLM schema (see `skills/agents/tools/web/fetch_web_page_text.py`).
- **`cmd/*.py`**: one **`CommandBase`** subclass per file, **`async def execute(self, app, args)`**; module basename → slash command (see `examples/skills/hello-world/cmd/echo.py`). Prefer **`preview_then_append_chat_message`** when injecting into chat.
- **`components/sidebar_tab.py`**: **`sidebar_label`** (str), plus **`get_sidebar_widget`** or **`SidebarWidget`** class; optional **`sidebar_tooltip`** (`utils/skill_components.py`).
- **`components/leader_menu.py`**: **`def register_leader(reg):`** with **`reg.add_submenu`** / **`reg.add_action`** (`examples/component/leader_menu.py`).
- **`components/**/*.css`**: Textual CSS; merged at startup for that skill.
- **Bundled sub-agents**: JSON under **`$CODY_DIR/skills/agents/bundled/`** (or the path from **`bundled_agent_definitions_dir()`**) — not per arbitrary skill folder unless you add files there deliberately.
- **Themes**: tiered **`themes/*.py`** exporting **`theme`** — see extension table in `extending_cody.md`.
- **Secrets**: **`password_vault.md`**; if the skill caches decrypted data, register **`register_vault_session_clear_hook`**.

**Restart Cody** after adding or changing `cmd/`, `tools/`, `components/`, or tiered tools so discovery runs again.

## Scripts (run_skill)

Default scaffold includes **cmd**, **tools**, **sidebar + CSS**, **leader menu**, and **scripts/hello.py**. Use **`--minimal`** for only `SKILL.md` + `scripts/hello.py`.

### Scaffold a new skill

```json
{
  "function": "run_skill",
  "arguments": {
    "skill_name": "cody-skill-author",
    "script_name": "scaffold_cody_skill.py",
    "args": "--target project --skill-dir-name my-skill --frontmatter-name my-skill --description \"Short catalog description.\""
  }
}
```

Optional flags: `--title "Human title"`; **`--minimal`** (no cmd/tools/components/leader); **`--force`** (overwrite existing directory).

`--target`: `project` → `{working_directory}/.agents/skills` (uses `CODY_WORKING_DIRECTORY` or cwd), `user` → `~/.agents/skills`, `bundled` → `$CODY_DIR/skills`.

### Validate a skill directory

```json
{
  "function": "run_skill",
  "arguments": {
    "skill_name": "cody-skill-author",
    "script_name": "validate_cody_skill.py",
    "args": "--path \"/absolute/path/to/skill-folder\""
  }
}
```

### Refresh reference docs (maintainers)

After editing repo `docs/*.md`, copy into this skill’s `reference/`:

- **Slash command:** **`/sync_reference_docs`** — same behavior as the script (notifies with a short log).

```json
{
  "function": "run_skill",
  "arguments": {
    "skill_name": "cody-skill-author",
    "script_name": "sync_reference_docs.py",
    "args": ""
  }
}
```

## Examples in the repo

- `examples/skills/hello-world/` — minimal skill + `cmd/`.
- `examples/component/` — sidebar and leader menu patterns.
