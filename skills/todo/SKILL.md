---
name: todo
description: Manage global and project-specific to-do tasks. Use when the user wants to add, list, update, edit, or delete tasks. Always call activate_skill before run_skill for this skill.
---

# Todo Skill

Tasks are stored in the Cody project database. Each task has a **scope**: `global` or a **working directory path** (use the session working directory for project-local tasks).

## Workflow

1. **Activate** — call `activate_skill` with skill name `todo` to load this file and script paths.
2. **Run scripts** — use `run_skill` with `skill_name` `todo` and the `script_name` below. Quote paths and free text in `args` so the shell parses them correctly.

Default scope: if the user does not specify, use the current project's working directory for local tasks; use `global` only when they clearly mean a general/life task.

## Scripts

| Script | Purpose |
|--------|---------|
| `add_todo.py` | Create a task |
| `list_todos.py` | List tasks (optional filters) |
| `update_todo_status.py` | Set `pending` or `completed` |
| `edit_todo.py` | Change label, text, deadline |
| `delete_todo.py` | Remove a task by id |

### add_todo.py

- `--label` — short title (required)
- `--scope` — `global` or working directory path (required)
- `--text` — detailed description (required)
- `--deadline` — optional (e.g. `YYYY-MM-DD`)

```json
{
  "function": "run_skill",
  "arguments": {
    "skill_name": "todo",
    "script_name": "add_todo.py",
    "args": "--label \"Fix login\" --scope \"/path/to/project\" --text \"Handle OAuth refresh\""
  }
}
```

### list_todos.py

- `--scope` — optional; `global`, a directory path, or omit for all scopes
- `--status` — optional; `pending` or `completed`

```json
{
  "function": "run_skill",
  "arguments": {
    "skill_name": "todo",
    "script_name": "list_todos.py",
    "args": "--status pending"
  }
}
```

### update_todo_status.py

- `--id` — database row id (required)
- `--status` — `pending` or `completed` (required)

```json
{
  "function": "run_skill",
  "arguments": {
    "skill_name": "todo",
    "script_name": "update_todo_status.py",
    "args": "--id 3 --status completed"
  }
}
```

### edit_todo.py

- `--id`, `--label`, `--text` — required
- `--deadline` — optional

### delete_todo.py

- `--id` — required

When you finish work the user asked for, you may mark the matching todo completed via `update_todo_status.py`.
