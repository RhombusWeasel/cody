---
name: git
description: A specialized skill set for Cody with dedicated scripts for performing git operations safely and efficiently. Always use this skill for git interactions and always call activate_skill before trying to use these tools.
---

# Git Skill

This skill provides a set of tools to interact with git repositories safely, replacing raw shell commands for git operations.

## Available Scripts

The following scripts are available in the `scripts/` directory. Run them using the `run_skill` tool.

When using `run_skill`, set the `skill_name` to `git` and the `script_name` to the desired script.

### 1. Status

Shows the current git status, including staged, unstaged, and untracked files.

```json
{
  "function": "run_skill",
  "arguments": {
    "skill_name": "git",
    "script_name": "status.py",
    "args": "--path \"/path/to/repo\""
  }
}
```

### 2. Diff

Shows the diff of changes. Can show staged or unstaged changes, for all files or a specific file.

```json
{
  "function": "run_skill",
  "arguments": {
    "skill_name": "git",
    "script_name": "diff.py",
    "args": "--path \"/path/to/repo\" [--file-path \"path/to/file\"] [--staged]"
  }
}
```

### 3. Stage

Stages changes for commit. Can stage a specific file or all changes.

```json
{
  "function": "run_skill",
  "arguments": {
    "skill_name": "git",
    "script_name": "stage.py",
    "args": "--path \"/path/to/repo\" [--file-path \"path/to/file\"]"
  }
}
```

### 4. Commit

Commits staged changes with a message.

```json
{
  "function": "run_skill",
  "arguments": {
    "skill_name": "git",
    "script_name": "commit.py",
    "args": "--path \"/path/to/repo\" --message \"Commit message\""
  }
}
```

### 5. Branch

Manage branches. Can list branches, create a new branch, or checkout an existing branch.

```json
{
  "function": "run_skill",
  "arguments": {
    "skill_name": "git",
    "script_name": "branch.py",
    "args": "--path \"/path/to/repo\" [--list] [--create \"new-branch-name\"] [--checkout \"branch-name\"]"
  }
}
```

### 6. Log

Shows recent commit history.

```json
{
  "function": "run_skill",
  "arguments": {
    "skill_name": "git",
    "script_name": "log.py",
    "args": "--path \"/path/to/repo\" [--count 10]"
  }
}
```
