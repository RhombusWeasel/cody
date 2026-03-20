---
name: todo
description: Manage global and project-specific to-do tasks. Use when the user wants to add, list, update, edit, or delete tasks. Always call activate_skill before run_skill for this skill.
---

# Todo Skill

Tasks are stored in the Cody project database. Each task has a **scope**: `global` or a **working directory path** (use the session working directory for project-local tasks).

Each row may also have:

- **`completion_note`** — text saved when the task is marked completed (cleared when set back to pending).
- **`completion_date`** — timestamp when completed (defaults to now when completing via script; cleared when set back to pending).
- **`comments`** — JSON array of strings (stored as text), e.g. `["note one","note two"]`. Use `append_todo_comment.py` to add one line without rewriting the whole list.

## Workflow

1. **Activate** — call `activate_skill` with skill name `todo` to load this file and script paths.
2. **Run scripts** — use `run_skill` with `skill_name` `todo` and the `script_name` below. Quote paths and free text in `args` so the shell parses them correctly.

Default scope: if the user does not specify, use the current project's working directory for local tasks; use `global` only when they clearly mean a general/life task.

## Scripts

| Script | Purpose |
|--------|---------|
| `add_todo.py` | Create a task |
| `list_todos.py` | List tasks (optional filters) |
| `update_todo_status.py` | Set `pending` or `completed` (note required when completing) |
| `edit_todo.py` | Change label, text, deadline; optionally comments / completion fields |
| `append_todo_comment.py` | Append one string to `comments` |
| `delete_todo.py` | Remove a task by id |

### add_todo.py

- `--label` — short title (required)
- `--scope` — `global` or working directory path (required)
- `--text` — detailed description (required)
- `--deadline` — optional (e.g. `YYYY-MM-DD`)
- `--comments` — optional JSON array of strings (default `[]`)

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

Output includes `completion_note`, `completion_date`, and `comments` (JSON string) for each task.

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
- `--completion-note` — **required** when `--status completed` (non-empty); briefly state why the task was closed. Ignored when setting `pending` (pending clears note and date).
- `--completion-date` — optional when completing (e.g. `YYYY-MM-DD`); omit for current time

```json
{
  "function": "run_skill",
  "arguments": {
    "skill_name": "todo",
    "script_name": "update_todo_status.py",
    "args": "--id 3 --status completed --completion-note \"Shipped in v2\""
  }
}
```

### edit_todo.py

- `--id`, `--label`, `--text` — required
- `--deadline` — optional
- `--comments` — optional; replaces the entire comments JSON array (omit to leave unchanged)
- `--completion-note`, `--completion-date` — optional (omit to leave unchanged)

### append_todo_comment.py

- `--id` — required
- `--text` — comment line to append (required)

```json
{
  "function": "run_skill",
  "arguments": {
    "skill_name": "todo",
    "script_name": "append_todo_comment.py",
    "args": "--id 3 --text \"Blocked on API review\""
  }
}
```

### delete_todo.py

- `--id` — required

When you finish work the user asked for, mark the matching todo completed via `update_todo_status.py` and always pass a non-empty `--completion-note` explaining why it was closed.
