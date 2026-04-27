---
name: file-manipulation
description: A specialized skill set for Cody with dedicated scripts for reading, creating, editing, and searching files safely and efficiently.  Always use this skill for file interactions and always call activate_skill before trying to use these tools.
---

# Coding Skill

This skill provides a set of tools to interact with the codebase safely, replacing raw shell commands for file operations.

## Available Scripts

The following scripts are available in the `scripts/` directory. Run them using the `run_skill` tool.

When using `run_skill`, set the `skill_name` to `file-manipulation` and the `script_name` to the desired script.

### 1. Write a File

Writes content to a file, creating parent directories as needed. Creates new files and **overwrites** existing ones.
Content can be provided via `--content` or piped through stdin (useful for multi-line content).

```json
{
  "function": "run_skill",
  "arguments": {
    "skill_name": "file-manipulation",
    "script_name": "write_file.py",
    "args": "--path \"path/to/file.py\" --content \"file content\""
  }
}
```

For multi-line content, pipe via stdin instead:
```json
{
  "function": "run_skill",
  "arguments": {
    "skill_name": "file-manipulation",
    "script_name": "write_file.py",
    "args": "--path \"path/to/file.py\""
  }
}
```

### 2. Read a File

Reads a file and outputs the content with line numbers for easy reference.

```json
{
  "function": "run_skill",
  "arguments": {
    "skill_name": "file-manipulation",
    "script_name": "read_file.py",
    "args": "--path \"path/to/file.py\""
  }
}
```

### 3. Edit a File

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

### 4. Search Code

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

### 5. Inspect a File

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
