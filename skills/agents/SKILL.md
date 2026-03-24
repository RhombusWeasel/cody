---
name: agents
description: Manage and invoke user-defined sub-agents to delegate specialised tasks
---

# Agents Skill

User-defined sub-agents are stored in the local database. Each agent has a name, description, system prompt, a restricted set of tool groups, and an optional provider/model override.

Optional **LLM tools** for this skill live under `skills/agents/tools/` (for example `tools/web/`). They are loaded at startup with the same tier and `skills.enabled` rules as slash commands—see [extending_cody.md](../../docs/extending_cody.md).

## Bundled example

Shipped JSON definitions live in `skills/agents/bundled/`. On database init, Cody inserts any agent whose `name` is not already in the `agents` table (see `bundled_agent_definitions_dir()` in `utils/paths.py`).

- **`page_summarizer`** — uses `web` (`fetch_web_page_text`) only: fetches public HTML URLs and converts them to markdown via `html-to-markdown`, then answers in markdown. Try: `/run_agent page_summarizer Summarize https://example.com` (after activating this skill so delegation is in context).

## Workflow

1. **Discover** — run `list_agents.py` to see what agents are available and what they do.
2. **Inspect** — run `get_agent.py --name <name>` to review an agent's full configuration before delegating to it.
3. **Delegate** — run `run_agent.py --name <name> --task "<task description>"` to invoke the agent and receive its result.

Always pass `--working-directory` to `run_agent.py` so the sub-agent has the correct working context.

## Scripts

- `list_agents.py` — lists all agents with name and description
- `get_agent.py --name NAME` — shows full detail for a single agent
- `run_agent.py --name NAME --task "TASK" [--working-directory PATH]` — runs the agent and returns its output
