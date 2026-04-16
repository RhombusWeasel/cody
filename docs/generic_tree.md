# GenericTree: flat sidebar trees

Reference for [`components/tree/generic_tree.py`](../components/tree/generic_tree.py) and related pieces. Use this when authoring **skills** (or other extensions) that need a hierarchical list with expand/collapse, per-row actions, and Cody-consistent styling.

## What it is

`GenericTree` is a **Textual** `Vertical` that renders a **flat list** of rows: one widget per **visible** tree line. There is **no nested widget tree** for children; depth is expressed with a string **indent prefix** (box-drawing characters) on each row.

That design keeps scrolling and layout predictable and matches how other Cody sidebars (files, git, DB, settings, vault) behave.

## Related modules

| Piece | Role |
|--------|------|
| [`GenericTree`](../components/tree/generic_tree.py) | Container: owns `_expanded`, rebuilds rows on refresh |
| [`TreeRow`](../components/tree/tree_row.py) | Default row: indent, expand chevron, icon + label, action buttons |
| [`TreeEntry`](../utils/tree_model.py) | Dataclass describing one visible line |
| [`NodeToggled` / `NodeSelected`](../components/tree/tree_row.py) | Messages posted when the user clicks a row (not a button) |
| [`components/tree/generic_tree.css`](../components/tree/generic_tree.css) | Striping and layout for `GenericTree` / `TreeRow` |
| [`components/utils/fs_tree.py`](../components/utils/fs_tree.py) | `path_entries_to_tree()` helper for directory-style trees |

Exports are also available from `components.tree`:

```python
from components.tree import GenericTree, TreeRow, NodeToggled, NodeSelected
```

## `TreeEntry` fields

Each call to `get_visible_entries()` returns a list of `TreeEntry` instances.

| Field | Meaning |
|--------|---------|
| `node_id` | Any hashable value identifying the node. Used for expand state, button callbacks, and messages. Often `str`, `Path`, or a small `tuple`/`dict` for composite keys (see Git tree). |
| `indent` | Prefix string before the chevron (e.g. `""`, `"├── "`, `"│   └── "`). Build from `GenericTree`’s branch constants (below). |
| `is_expandable` | If true, row shows chevron and click posts `NodeToggled`. |
| `is_expanded` | Whether the chevron points down (visual only; expand state is also tracked in `_expanded`). |
| `display_name` | Plain text label after the node icon. |
| `icon` | String (usually a single glyph from Nerd Fonts via [`utils/icons.py`](../utils/icons.py)). |
| `display_rich` | Optional `rich.text.Text` for styled labels; when set, row uses Rich instead of plain `display_name` for the label body (icon still prepended). |
| `row_variant`, `vault_*` | Used by vault-specific rows; see **Custom row widgets**. |

## `GenericTree` API

### Constructor

```python
GenericTree(root_node_id: Any | None = None, icon_set: dict[str, str] | None = None, **kwargs)
```

- **`root_node_id`**: If set, the default `on_node_toggled` **ignores** toggle clicks on that id (used by [`FileTree`](../components/fs/file_tree.py) so the workspace root does not collapse).
- **`icon_set`**: Merged onto [`DEFAULT_ICON_SET`](../utils/icons.py) (`folder`, `file`, `database`, `git`, `skill`). Use `self.icon("folder")` etc. to resolve keys.

### Drawing constants (class attributes)

Use these when building `indent` strings so trees align:

- `BRANCH` → `"├── "`
- `LAST_BRANCH` → `"└── "`
- `VERTICAL` → `"│   "` (continuing branch)
- `SPACER` → `"    "` (branch ended above)

**Patterns:**

- **One level under a parent:** prefix children with `VERTICAL` or `SPACER` depending on whether the parent was the last sibling, then add `BRANCH` or `LAST_BRANCH` per child. See [`GitTree._build_category`](../skills/git/components/git_tree.py).
- **Deep dict/config walks:** keep an `ancestors_last: list[bool]` and build `"".join(SPACER if last else VERTICAL for last in ancestors_last)` before the branch symbol. See [`SettingsTree`](../components/sidebar/settings.py).
- **Filesystem:** call `fs_tree.path_entries_to_tree(...)` with the same four symbols and `expanded=self._expanded`. See [`FileTree`](../components/fs/file_tree.py) and [`SkillsTree`](../components/sidebar/tool_list.py).

### Methods you must implement

#### `get_visible_entries(self) -> list[TreeEntry]`

Return **only rows that should appear**, in order, top to bottom. You decide what “expanded” means by checking `self._expanded` (a `set`) and emitting child rows only when parents are expanded.

The base class **does not** walk a separate graph; **you** flatten your model into rows.

#### `get_node_buttons(self, node_id: Any, is_expandable: bool) -> list[Button]`

Return the action buttons for that row. The base class attaches `node_id` to each button for internal use. Typical pattern: `ActionButton`, `EditButton`, `DeleteButton` from [`components/utils/buttons.py`](../components/utils/buttons.py) with `action=lambda n=node_id: self.on_button_action(n, "…")`.

Return `[]` for rows with no actions.

### Methods you may override

| Method | Default behavior |
|--------|-------------------|
| `load_children_async(self, node_id)` | No-op. Called **before** `on_node_toggled` when the user expands a node that is not yet in `_expanded`. Use for lazy I/O (remote lists, large dirs). |
| `on_node_toggled(self, node_id)` | Toggles membership in `_expanded` (skips `root_node_id`), then `_refresh()`. |
| `on_node_selected(self, node_id)` | No-op. Override for leaf clicks. |
| `on_button_action(self, node_id, action)` | No-op. Central place to dispatch button `action` strings. |
| `create_row_widget(self, entry)` | Builds a `TreeRow` from `entry`. Override to inject custom row widgets (see below). |

### Methods to call from your code

- **`reload()`** — Rebuild all rows from `get_visible_entries()`. Call after data changes (DB update, config save, etc.).
- **`icon(key)`** — Resolve a key from the merged icon set; falls back to file icon.

### Lifecycle

- On mount, `GenericTree` calls `_refresh()` once.
- Internal handlers: `@on(NodeToggled)` runs `await load_children_async(node_id)` when expanding, then `on_node_toggled(node_id)`. `@on(NodeSelected)` calls `on_node_selected`.

## `TreeRow` click behavior

- Clicks on a **Button** are left to the button.
- Other clicks **stop propagation** and post:
  - **`NodeToggled(node_id)`** if `is_expandable`
  - **`NodeSelected(node_id)`** if not

Both message types **bubble**. A parent container can handle selection without subclassing the tree:

```python
from textual import on
from components.tree import NodeSelected

@on(NodeSelected)
def on_skill_node_selected(self, event: NodeSelected) -> None:
  node_id = event.node_id
  ...
```

Example: [`ToolList`](../components/sidebar/tool_list.py).

## Custom row widgets

Override `create_row_widget` to return something other than `TreeRow` for specific entries (e.g. vault secret lines).

- Set a discriminator on `TreeEntry` (vault uses `row_variant="vault_secret_line"` and related fields).
- Delegate unknown variants to `super().create_row_widget(entry)`.

Example: [`PasswordVaultTree`](../components/sidebar/password_vault_tree.py).

Custom rows that should behave like normal nodes must replicate click → `NodeToggled` / `NodeSelected` (see `TreeRow`). Pure display rows (like `VaultSecretLineRow`) do not need to.

## Styling

Core rules live in [`components/tree/generic_tree.css`](../components/tree/generic_tree.css) (striped `TreeRow`, auto height).

For **custom row classes**, add alternating rules alongside the existing `VaultSecretLineRow` / `AgentDescriptionRow` pattern:

```css
GenericTree .tree_rows YourRow:even { background: $surface; }
GenericTree .your_rows YourRow:odd { background: $surface-lighten-2; }
```

**Skills:** place CSS under `<skill-dir>/components/**/*.css`; the app merges those paths at startup (see [extending_cody.md](extending_cody.md)).

## Skill checklist

1. **Subclass** `GenericTree` in e.g. `<skill>/components/your_tree.py`.
2. **Implement** `get_visible_entries` and `get_node_buttons` (and usually `on_button_action`).
3. **Track expansion** via `self._expanded`; optionally seed defaults in `__init__` (many trees call `self._expanded.update([...])` for initially open sections).
4. **Refresh** after async loads: call `self.reload()` on the UI thread when data is ready (Cody trees often use Textual `@work` workers that finish with `reload()`).
5. **Expose the widget** from your skill’s `sidebar_tab` (or other compose path) via `get_sidebar_widget()` / compose.
6. **Optional:** `icon_set={**icons.DEFAULT_ICON_SET, "my_kind": "…"}` for named icons; use `self.icon("my_kind")` in entries.
7. **Optional:** `@on(NodeSelected)` on a parent if selection logic belongs outside the tree class.
8. **Filesystem-like trees:** reuse `fs_tree.path_entries_to_tree` with `self._expanded` and the four branch constants.

## In-repo examples

| Tree | File | Notes |
|------|------|--------|
| File browser | [`components/fs/file_tree.py`](../components/fs/file_tree.py) | `root_node_id`, `path_entries_to_tree` |
| Git sidebar | [`skills/git/components/git_tree.py`](../skills/git/components/git_tree.py) | Rich labels, tuple/dict `node_id`s, categories |
| Todos | [`skills/todo/components/todo_tree.py`](../skills/todo/components/todo_tree.py) | Simple sections + DB-backed leaves |
| Skills file tree | [`components/sidebar/tool_list.py`](../components/sidebar/tool_list.py) | `SkillsTree` + parent `NodeSelected` |
| Settings | [`components/sidebar/settings.py`](../components/sidebar/settings.py) | Recursive config walk, indent builder |
| Vault | [`components/sidebar/password_vault_tree.py`](../components/sidebar/password_vault_tree.py) | `create_row_widget`, custom icon set |
| DB | [`components/db/db_tree.py`](../components/db/db_tree.py) | DB schema exploration |

## Design constraints

- **`node_id` must be usable as a set element** (for `_expanded`) and stable across refreshes for the same logical node.
- **Rebuild cost:** every `reload()`/`_refresh()` removes and remounts all row widgets. Fine for typical sidebar sizes; avoid huge flat lists without virtualization (not built into `GenericTree`).
- **Threading:** mutate app state and call `reload()` from Textual-appropriate contexts after async work (same patterns as existing `@work` trees).

For broader extension hooks (sidebar discovery, CSS paths), see [extending_cody.md](extending_cody.md).
