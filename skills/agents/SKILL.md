---
name: agents
description: Manage and invoke user-defined sub-agents to delegate specialised tasks
---

# Agents Skill

User-defined sub-agents are stored in the local database. Each agent has a name, description, system prompt, a restricted set of tool groups, and an optional provider/model override.

## Workflow

1. **Discover** — run `list_agents.py` to see what agents are available and what they do.
2. **Inspect** — run `get_agent.py --name <name>` to review an agent's full configuration before delegating to it.
3. **Delegate** — run `run_agent.py --name <name> --task "<task description>"` to invoke the agent and receive its result.

Always pass `--working-directory` to `run_agent.py` so the sub-agent has the correct working context.

## Scripts

- `list_agents.py` — lists all agents with name and description
- `get_agent.py --name NAME` — shows full detail for a single agent
- `run_agent.py --name NAME --task "TASK" [--working-directory PATH]` — runs the agent and returns its output
