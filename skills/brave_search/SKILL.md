---
name: brave-search
description: Search the web with the Brave Search API. Use after activate_skill when the user needs current web results, citations, or fact-checking. API token is stored only in the password vault (Vault tab or prompted on first Brave sidebar search when the key is missing).
---

# Brave Search

Run **`activate_skill`** with this skill first, then use **`run_skill`** with `skill_name` **`brave-search`**.

## Token

- Get a subscription token from [Brave Search API](https://brave.com/search/api).
- In Cody, unlock the **password vault**, add the token under **Vault → Credentials → default** as **Brave Search API** (row is created when you unlock the Vault tab or run a Brave sidebar search), or enter it when the sidebar prompts on first search. Expand the row and use the **eye** icon to reveal the token (it stays masked until then).
- **`run_skill`** subprocesses receive the token only when the vault is **unlocked** in the same Cody process.

## Script: `search_web.py`

Returns **JSON on stdout** (parsed from the tool result).

```json
{
  "function": "run_skill",
  "arguments": {
    "skill_name": "brave-search",
    "script_name": "search_web.py",
    "args": "--query \"your search terms\""
  }
}
```

Optional: `--limit 5` (integer, max 20). If omitted, uses config **`brave_search.max_results`** (default 10).

## Response shape

Success:

```json
{
  "query": "...",
  "results": [
    { "title": "...", "url": "https://...", "description": "..." }
  ]
}
```

Error:

```json
{ "error": "..." }
```

## Sidebar

The Brave Search sidebar tab supports the same query with clickable result links (opens the system browser).
