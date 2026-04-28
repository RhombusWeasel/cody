---
name: file-manipulation
description: A specialized skill set for Cody with dedicated scripts for reading, creating, editing, and searching files safely and efficiently.  Always use this skill for file interactions and always call activate_skill before trying to use these tools.
---

# Coding Skill

This skill provides tools to interact with the codebase safely, replacing raw shell commands for file operations.

## System Tools (no skill activation needed)

The following file operations are available as **system tools** — call them directly without activating this skill:

- **`read_file(path, start_line, end_line)`** — Read a file with optional line range. Shows line numbers.
- **`write_file(path, lines)`** — Write a file. Provide `lines` (list of strings joined with newlines). Creates parent directories automatically.

These accept proper typed parameters, so there's no escaping or heredoc hassle.

## Skill Scripts (activate this skill first)

The following scripts are available in the `scripts/` directory. Run them using the `run_skill` tool with `skill_name` set to `file-manipulation`.

### 1. Edit a File

A robust editing script that performs exact string replacement to avoid rewriting entire files for small changes.

```json
{
  "function": "run_skill",
  "arguments": {
    "skill_name": "file-manipulation",
    "script_name": "edit_file.py",
    "args": "--path \"path/to/file.py\" --old-text \"text to replace\" --new-text \"new text\""
  }
}
```

### 2. Search Code

Searches for specific strings or regex patterns across the workspace.

```json
{
  "function": "run_skill",
  "arguments": {
    "skill_name": "file-manipulation",
    "script_name": "search_code.py",
    "args": "--pattern \"search pattern\""
  }
}
```

### 3. Inspect a File

Provides code-aware structural analysis of source files. Shows a table-of-contents summary
(functions, classes, etc.) or extracts specific sections by name or line range.
Supports Python (AST-based) and Lua (regex-based) parsers.

```json
{
  "function": "run_skill",
  "arguments": {
    "skill_name": "file-manipulation",
    "script_name": "inspect_file.py",
    "args": "--path \"path/to/file.py\" --summary"
  }
}
```

Extract a specific function:
```json
{
  "function": "run_skill",
  "arguments": {
    "skill_name": "file-manipulation",
    "script_name": "inspect_file.py",
    "args": "--path \"path/to/file.py\" --function my_function"
  }
}
```

Extract a line range with context:
```json
{
  "function": "run_skill",
  "arguments": {
    "skill_name": "file-manipulation",
    "script_name": "inspect_file.py",
    "args": "--path \"path/to/file.py\" --lines 10-45 --context 3"
  }
}
```

List registered parsers:
```json
{
  "function": "run_skill",
  "arguments": {
    "skill_name": "file-manipulation",
    "script_name": "inspect_file.py",
    "args": "--list-parsers"
  }
}
```
