---
name: Todo App
description: Manage global and project-specific to-do tasks. Use this skill when the user wants to add, list, update, edit, or delete tasks.
---

# Todo App Skill

This skill allows you to manage a to-do list for the user. Tasks can be either `global` or specific to the current project (`working_directory`).

## Tools Available
- `add_todo(label, scope, todo_text, deadline)`: Add a new task. `scope` should be either 'global' or the current working directory path.
- `get_todos(scope, status)`: List tasks for a given scope and optional status ('pending' or 'completed').
- `update_todo_status(todo_id, status)`: Mark a task as 'pending' or 'completed'.
- `edit_todo(todo_id, label, todo_text, deadline)`: Edit an existing task.
- `delete_todo(todo_id)`: Delete a task.

## Usage
When a user asks to add a task, use `add_todo`. If they don't specify a scope, default to the current project's working directory unless they imply it's a general task, in which case use 'global'.
When a user asks what tasks are pending, use `get_todos`.
When you complete a task for the user, you can proactively use `update_todo_status` to mark it as 'completed'.
