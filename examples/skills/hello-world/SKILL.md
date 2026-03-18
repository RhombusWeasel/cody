---
name: hello-world
description: A simple example skill that demonstrates how to create and use custom skills in Cody.
---

# Hello World Skill

This is a basic example of a custom skill. It provides a simple script that greets the user.

## Available Scripts

The following script is available in the `scripts/` directory. Run it using the `run_skill` tool.

### 1. Say Hello

Prints a friendly greeting. You can optionally provide a name.

```json
{
  "function": "run_skill",
  "arguments": {
    "skill_name": "hello-world",
    "script_name": "hello.py",
    "args": "--name \"Pete\""
  }
}
```
