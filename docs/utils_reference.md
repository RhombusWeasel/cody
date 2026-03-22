# Utils reference

Structured reference for [`utils/`](../utils/). Each section uses the same shape: **Purpose**, **Use when**, **Primary API**, **Depends on**.

For how to extend Cody (skills, tools, commands, themes), see [extending_cody.md](extending_cody.md).

## Read this first

- **[`paths.py`](#pathspy)** — Resolves `$CODY_DIR`, `~/.agents`, and `{working_directory}/.agents` for any tiered resource; includes `bundled_agent_definitions_dir()` for shipped sub-agent JSON.
- **[`cfg_man.py`](#cfg_manpy)** — Merged JSON config; dotted keys (`interface.theme`).
- **[`skills.py`](#skillspy)** — Skill discovery from `SKILL.md`; feeds the agent catalog and optional skill UI hooks.

---

## agent.py

**Purpose:** Builds the chat agent message list with system prompt (including `{working_directory}` substitution), injects the skills XML catalog, and runs LLM turns via the active provider and registered tools.

**Use when:** Implementing or debugging chat behavior, provider/tool wiring, or how skills appear in the system prompt.

**Primary API:** `Agent` (`__init__`, `add_msg`, `get_response`), `TaskAgent` (`__init__`, `add_msg`, `run` — async loop with a fixed tool list).

**Depends on:** `utils.tool`, `utils.cfg_man`, `utils.skills`, `utils.providers`.

---

## cfg_man.py

**Purpose:** Layered JSON configuration with deep merge, dotted-path get/set, code-registered defaults, and save. The active `save_path` (usually `{working_directory}/.agents/cody_config.json`) stores a **deep overlay**: only keys that differ from the merge of all lower-precedence files on disk (`~/.agents/cody_settings.json`, then `$CODY_DIR/.agents/cody_config.json` when present).

**Use when:** Reading or writing settings, merging skill `config.json` into `cfg.data`, registering defaults (`register_default_config`), calling `cfg.apply_registered_defaults()` after `load_project_config`, or understanding load/save order.

**Primary API:** `deep_update`, `deep_merge_missing`, `register_default_config`, `Config` (`load_all`, `load_project_config`, `apply_registered_defaults`, `get`, `set`, `drill`, `save`), module singleton `cfg`.

**Depends on:** `utils.paths` (default config paths under `~/.agents` and `$CODY_DIR`).

---

## cmd_loader.py

**Purpose:** Loads chat slash commands from configured dirs (default `$CODY_DIR/cmd` via `default_command_directory_templates`), then from each enabled skill’s `cmd/` folder in skills tier order; each module exposes one `CommandBase` subclass.

**Use when:** Adding or listing slash commands; overriding names via later-loaded directories.

**Primary API:** `CommandBase`, `load_commands()`.

**Depends on:** `utils.cfg_man`, `utils.paths`, `utils.skills` (`skill_command_directory_paths`).

---

## db.py

**Purpose:** SQLite connection manager for app data (chats, input history, agents, user DB connections, etc.). The bundled Cody DB file lives at `$CODY_DIR/.agents/cody_data.db` (install directory from `get_cody_dir()`), not under `{working_directory}/.agents`.

**Use when:** Persisting or querying chat/history/agent records from UI or tools.

**Primary API:** `DatabaseManager` (`get_project_db_path`, `add_connection`, async helpers as used by components), module `db_manager`. On init, `_seed_bundled_agents` inserts agents from JSON in [`bundled_agent_definitions_dir()`](#pathspy) when the agent `name` is missing.

**Depends on:** `utils.cfg_man`; `utils.paths` (`get_cody_dir`, `bundled_agent_definitions_dir`).

---

## editors.py

**Purpose:** Maps file extensions to Textual language ids and opens `EditorTab` in the workspace on the UI thread.

**Use when:** Opening a file for in-app editing from anywhere that has the Textual `app` reference.

**Primary API:** `LANG_MAP`, `open_file_editor(app, path, on_saved=...)`.

**Depends on:** `components.workspace` (lazy import).

---

## fs.py

**Purpose:** Small JSON helpers, recursive CSS discovery, and dynamic import of all `.py` files under a directory (used for tools).

**Use when:** Loading JSON assets, collecting CSS paths, or mirroring how `main.py` loads tiered `tools/` and each skill’s `tools/` root.

**Primary API:** `save_data`, `load_data`, `discover_css`, `load_folder`.

**Depends on:** stdlib only.

---

## git.py

**Purpose:** GitPython wrappers for repo detection, init, checkpoints, status/diff parsing, branches, stashes, merge/revert/rename.

**Use when:** Git sidebar, automation around snapshots, or any feature that needs porcelain-style file status.

**Primary API:** `is_git_repo`, `ensure_git_repo`, `create_checkpoint`, `revert_to_checkpoint`, `get_file_status`, `get_branches_info`, `get_recent_commits`, stash/merge helpers, etc.

**Depends on:** `git` package.

---

## icons.py

**Purpose:** Nerd Font codepoint constants for consistent glyphs across the TUI.

**Use when:** Adding UI that should match existing sidebar/action iconography.

**Primary API:** Module-level constants (`CHATS`, `FILE_SYSTEM`, `FOLDER`, …).

**Depends on:** none.

---

## leader_registry.py

**Purpose:** Mergeable tree of leader-key chords; core modules and skills register submenus and leaf actions.

**Use when:** Adding global shortcuts behind the leader menu, or implementing `register_leader(reg)` in a skill.

**Primary API:** `reset_leader_registry`, `register_submenu`, `register_action`, `get_leader_root`, `LeaderRegistrar`, `register_core_leader_chords`, `discover_leader_entries`.

**Depends on:** `utils.skills`.

---

## password_vault.py

**Purpose:** Encrypted credential/note store at `~/.agents/cody_passwords_db.enc` (Fernet + PBKDF2), session unlock state.

**Use when:** Vault UI, locking/unlocking, CRUD on stored secrets.

**Primary API:** `vault_path`, `is_unlocked`, `clear_session_key`, load/save/list helpers (see module for full set).

**Developer guide:** [password_vault.md](password_vault.md).

**Depends on:** `cryptography`.

---

## paths.py

**Purpose:** Cody install dir, global `~/.agents`, template expansion, standard three-tier search order, command/theme path helpers.

**Use when:** Resolving where user or project content lives, or building config defaults for new tiered features.

**Primary API:** `get_cody_dir`, `get_global_agents_dir`, `bundled_agent_definitions_dir`, `tiered_dir_templates`, `resolve_dir_templates`, `resolved_tiered_paths`, `get_tiered_paths`, `parse_directory_list`, `default_command_directory_templates`, `resolved_theme_paths`.

**Depends on:** stdlib only.

---

## skill_components.py

**Purpose:** Discovers optional `components/sidebar_tab.py` inside each skill and returns tab metadata for the sidebar.

**Use when:** Implementing skill-provided sidebar tabs (`sidebar_label`, `get_sidebar_widget` or `SidebarWidget`).

**Primary API:** `discover_sidebar_tabs()`.

**Depends on:** `utils.skills`.

---

## skills.py

**Purpose:** Finds `SKILL.md` under configured directories, parses frontmatter, merges optional `config.json`, respects `skills.enabled`, exposes XML catalog for the agent.

**Use when:** Anything involving skill listing, body text, paths, or disabling a skill by name.

**Primary API:** `parse_frontmatter`, `skill_command_directory_paths`, `skill_tools_directory_paths`, `SkillManager` (`discover_skills`, `get_catalog_xml`, `get_skill`), `skill_manager`.

**Depends on:** `utils.cfg_man`, `utils.paths`.

---

## theme_man.py

**Purpose:** Loads Textual themes from `.py` files that define a `theme` object, scanning tiered theme directories.

**Use when:** Registering custom themes or debugging theme discovery.

**Primary API:** `discover_themes()`.

**Depends on:** `utils.paths`, `utils.cfg_man`.

---

## tool.py

**Purpose:** Global registry of LLM-callable tools: register by name, optional tag groups, enable/disable per tool or group, execution and schema consumers.

**Use when:** Implementing a new tool module (call `register_tool` at import) or toggling tools from the UI.

**Primary API:** `register_tool`, `get_tools`, `get_enabled_tool_functions`, `execute_tool`, group helpers (`toggle_group`, `set_group_enabled`, …), `get_tool_state_snapshot`.

**Depends on:** stdlib only.

---

## tree_model.py

**Purpose:** Dataclass for one row in generic tree UIs (file tree, vault, etc.).

**Use when:** Building list/tree views that share the same row shape (indent, expand state, icons, vault fields).

**Primary API:** `TreeEntry`.

**Depends on:** stdlib only.

---

## providers/__init__.py

**Purpose:** Selects provider implementation from config and returns model/options for chat calls.

**Use when:** Switching or adding backends at the integration point (not usually from skills).

**Primary API:** `PROVIDERS`, `get_provider()`, `get_provider_config()`.

**Depends on:** `utils.cfg_man`, concrete provider classes.

---

## providers/base.py

**Purpose:** Shared types for normalized chat responses and tool calls across Ollama and OpenAI adapters.

**Use when:** Typing or constructing provider responses in tests or new providers.

**Primary API:** `ToolCall`, `Message`, `ChatResponse`, `BaseProvider` (protocol).

**Depends on:** stdlib only.

---

## providers/ollama.py

**Purpose:** Ollama client adapter; maps native response to `ChatResponse`.

**Use when:** Debugging Ollama-specific behavior or options passed through `provider.chat`.

**Primary API:** `OllamaProvider.chat`.

**Depends on:** `ollama`, `utils.providers.base`.

---

## providers/openai.py

**Purpose:** OpenAI-compatible API client; converts message/tool-call formats and builds tool schemas from callables.

**Use when:** Debugging OpenAI path or message shape issues.

**Primary API:** `OpenAIProvider.chat`.

**Depends on:** `openai`, `utils.cfg_man`, `utils.providers.base`, `utils.providers.tools`.

---

## providers/tools.py

**Purpose:** Builds OpenAI-style JSON schemas from Python functions (signature types + Google-style `Args:` docstring lines).

**Use when:** Extending how tools are described to the OpenAI API.

**Primary API:** `callable_to_openai_schema`, `callables_to_openai_tools`.

**Depends on:** stdlib only.
