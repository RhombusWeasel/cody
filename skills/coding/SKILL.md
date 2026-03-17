---
name: file-manipulation
description: A specialized skill set for Cody with dedicated scripts for reading, creating, editing, and searching files safely and efficiently.  Always use this skill for file interactions and always call activate_skill before trying to use these tools.
---

# Coding Skill

This skill provides a set of tools to interact with the codebase safely, replacing raw shell commands for file operations.

## Available Scripts

The following scripts are available in the `scripts/` directory. Run them using the `run_skill` tool.

When using `run_skill`, set the `skill_name` to `file-manipulation` and the `script_name` to the desired script.

### 1. Create a File

Creates a new file. It will abort if the file already exists to prevent accidental overwrites.
--path and --content arguments must always be wrapped in quotes to ensure they are captured correctly.

```json
{
  "function": "run_skill",
  "arguments": {
    "skill_name": "file-manipulation",
    "script_name": "create_file.py",
    "args": "--path \"path/to/file.py\" --content \"file content\""
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

A robust editing script that performs exact string replacement to avoid catting entire files.

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
