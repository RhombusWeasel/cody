---
name: postit
description: Save, share, and run HTTP requests from tiered postit JSON collections (Postman-style). Use when the user wants to list, save, or execute saved API requests. Always call activate_skill before run_skill for this skill.
---

# Postit skill

Request definitions live as **one JSON file per request** in tiered `postit/` directories (same layout as `tools/`):

1. `$CODY_DIR/postit/`
2. `~/.agents/postit/`
3. `{working_directory}/.agents/postit/`

Later tiers **override** earlier ones when two files share the same stem (filename without `.json`). Only **top-level** `*.json` files in each folder are loaded (no subfolder recursion).

## JSON schema

Each file describes the full state of one request:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `version` | int | no | default `1` |
| `method` | string | yes | `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `HEAD`, `OPTIONS` |
| `url` | string | yes | Full URL |
| `headers` | object | no | String keys and values; default `{}` |
| `body` | string | no | Request body (raw); default `""` |
| `name` | string | no | Display hint (filename stem is still the collection key) |
| `label` | string | no | Same as `name` for display |

Example:

```json
{
  "version": 1,
  "method": "POST",
  "url": "https://api.example.com/v1/items",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "Bearer TOKEN"
  },
  "body": "{\"name\": \"demo\"}"
}
```

## Workflow

1. **Activate** — `activate_skill` with skill name `postit`.
2. **List** — `list_postit.py` to see merged request stems and sources.
3. **Run** — `run_postit.py --name STEM [--working-directory PATH]` to execute a merged request (prints status, response headers snippet, body).
4. **Save** — `save_postit.py --stem STEM --working-directory PATH --json-file PATH` (or omit `--json-file` to read JSON from stdin) to write into `{wd}/.agents/postit/{stem}.json`.

The TUI sidebar tab provides the same operations interactively.

## Scripts

| Script | Purpose |
|--------|---------|
| `list_postit.py` | List merged stems with tier source |
| `run_postit.py` | Run one request by stem |
| `save_postit.py` | Save a request JSON into the project `postit` tier |

### list_postit.py

```json
{
  "function": "run_skill",
  "arguments": {
    "skill_name": "postit",
    "script_name": "list_postit.py",
    "args": "--working-directory \"/path/to/project\""
  }
}
```

### run_postit.py

- `--name` — stem (required), e.g. `my-api` for `my-api.json`
- `--working-directory` — optional; default cwd
- `--timeout` — seconds (default 30)

### save_postit.py

- `--stem` — filename stem (required)
- `--working-directory` — project root (required for target dir)
- `--json-file` — path to JSON; if omitted, stdin

```json
{
  "function": "run_skill",
  "arguments": {
    "skill_name": "postit",
    "script_name": "save_postit.py",
    "args": "--stem my-api --working-directory \"/path/to/project\" --json-file \"/path/to/payload.json\""
  }
}
```
