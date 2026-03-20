import json
from typing import Any
from textual.widgets import Button
from textual import work

from components.tree.generic_tree import GenericTree
from utils.tree_model import TreeEntry
from utils.db import db_manager
from utils.paths import canonical_todo_scope, local_todo_scope_match_values
from skills.todo.scripts import todo_store


def _format_todo_handoff_message(label: str, todo_text: str, deadline: str) -> str:
    parts = [f"**Task:** {label}", ""]
    if todo_text:
        parts.append(todo_text)
        parts.append("")
    if deadline:
        parts.append(f"**Deadline:** {deadline}")
        parts.append("")
    parts.append("---")
    parts.append("")
    parts.append(
        "Please complete this task as described above. When you are done, mark the todo "
        "completed using the todo skill (activate_skill + run_skill update_todo_status.py); "
        "a non-empty --completion-note is required when marking completed."
    )
    return "\n".join(parts).strip()


class TodoTree(GenericTree):
    """Tree view for displaying and managing todos for a specific scope."""

    def __init__(self, scope: str, **kwargs):
        super().__init__(**kwargs)
        self.scope = canonical_todo_scope(scope)
        self._todos = []
        self._expanded.update(["pending", "completed"])

    def on_mount(self) -> None:
        super().on_mount()
        self.load_todos()

    @work
    async def load_todos(self) -> None:
        db_path = db_manager.get_project_db_path()
        if self.scope == "global":
            query = 'SELECT id, label, status FROM todos WHERE scope = ? ORDER BY creation_time DESC'
            params = ("global",)
        else:
            aliases = local_todo_scope_match_values(self.scope)
            placeholders = ",".join("?" * len(aliases))
            query = f'SELECT id, label, status FROM todos WHERE scope IN ({placeholders}) ORDER BY creation_time DESC'
            params = tuple(aliases)
        try:
            columns, rows = await db_manager.execute(db_path, query, params)
            self._todos = [{"id": r[0], "label": r[1], "status": r[2]} for r in rows]
            self.reload()
        except Exception as e:
            print(f"Failed to load todos: {e}")

    def get_visible_entries(self) -> list[TreeEntry]:
        entries = []
        pending = [t for t in self._todos if t["status"] == "pending"]
        completed = [t for t in self._todos if t["status"] in ("completed", "complete")]
        
        entries.append(TreeEntry(
            node_id="pending",
            indent="",
            is_expandable=True,
            is_expanded="pending" in self._expanded,
            display_name="Pending",
            icon="📋"
        ))
        
        if "pending" in self._expanded:
            if not pending:
                entries.append(TreeEntry(
                    node_id="empty_pending",
                    indent=self.LAST_BRANCH,
                    is_expandable=False,
                    is_expanded=False,
                    display_name="(none)",
                    icon=" "
                ))
            else:
                for i, todo in enumerate(pending):
                    is_last = i == len(pending) - 1
                    branch = self.LAST_BRANCH if is_last else self.BRANCH
                    entries.append(TreeEntry(
                        node_id=todo["id"],
                        indent=branch,
                        is_expandable=False,
                        is_expanded=False,
                        display_name=todo["label"],
                        icon="⏳"
                    ))
                    
        entries.append(TreeEntry(
            node_id="completed",
            indent="",
            is_expandable=True,
            is_expanded="completed" in self._expanded,
            display_name="Completed",
            icon="📋"
        ))
        
        if "completed" in self._expanded:
            if not completed:
                entries.append(TreeEntry(
                    node_id="empty_completed",
                    indent=self.LAST_BRANCH,
                    is_expandable=False,
                    is_expanded=False,
                    display_name="(none)",
                    icon=" "
                ))
            else:
                for i, todo in enumerate(completed):
                    is_last = i == len(completed) - 1
                    branch = self.LAST_BRANCH if is_last else self.BRANCH
                    entries.append(TreeEntry(
                        node_id=todo["id"],
                        indent=branch,
                        is_expandable=False,
                        is_expanded=False,
                        display_name=todo["label"],
                        icon="✅"
                    ))

        return entries

    def get_node_buttons(self, node_id: Any, is_expandable: bool) -> list[Button]:
        from components.utils.buttons import ActionButton, EditButton, DeleteButton
        from utils.icons import AI_HANDOFF, CHECKED, UNCHECKED, FOLDER
        todo = next((t for t in self._todos if t["id"] == node_id), None)
        if not todo:
            return []
        
        is_completed = todo["status"] in ("completed", "complete")
        status_btn_label = CHECKED if is_completed else UNCHECKED
        status_action = "pending" if is_completed else "completed"
        status_tooltip = "Mark Pending" if is_completed else "Mark Complete"
        
        is_global = self.scope == "global"
        scope_btn_label = FOLDER if is_global else ""
        scope_action = "local" if is_global else "global"
        scope_tooltip = "Move to Local" if is_global else "Move to Global"

        buttons: list[Button] = [
            ActionButton(status_btn_label, action=lambda n=node_id, s=status_action: self.on_button_action(n, f"status_{s}"), tooltip=status_tooltip, classes="action-btn"),
        ]
        if not is_completed:
            buttons.append(
                ActionButton(
                    AI_HANDOFF,
                    action=lambda n=node_id: self.on_button_action(n, "handoff_ai"),
                    tooltip="New chat: hand off to AI",
                    classes="action-btn",
                )
            )
        buttons.extend([
            ActionButton(scope_btn_label, action=lambda n=node_id, s=scope_action: self.on_button_action(n, f"scope_{s}"), tooltip=scope_tooltip, classes="action-btn"),
            EditButton(action=lambda n=node_id: self.on_button_action(n, "edit")),
            DeleteButton(action=lambda n=node_id: self.on_button_action(n, "delete")),
        ])
        return buttons

    def on_button_action(self, node_id: Any, action: str) -> None:
        if action.startswith("status_"):
            new_status = action.split("_")[1]
            self.update_status(node_id, new_status)
        elif action.startswith("scope_"):
            new_scope = action.split("_")[1]
            self.update_scope(node_id, new_scope)
        elif action == "edit":
            self.edit_todo(node_id)
        elif action == "delete":
            self.delete_todo(node_id)
        elif action == "handoff_ai":
            self.handoff_todo_to_chat(node_id)

    @work
    async def handoff_todo_to_chat(self, node_id: Any) -> None:
        from components.sidebar.chat_history import OpenChatWithSeedMessage

        db_path = db_manager.get_project_db_path()
        query = "SELECT label, todo_text, deadline FROM todos WHERE id = ?"
        try:
            _, rows = await db_manager.execute(db_path, query, (node_id,))
            if not rows:
                return
            r = rows[0]
            label = r[0] or ""
            body = (r[1] or "").strip()
            deadline = (r[2] or "").strip()
            text = _format_todo_handoff_message(label, body, deadline)
            self.post_message(OpenChatWithSeedMessage(text))
        except Exception as e:
            print(f"Failed to hand off todo: {e}")

    @work
    async def update_scope(self, node_id: Any, scope_type: str) -> None:
        from utils.cfg_man import cfg
        raw = "global" if scope_type == "global" else cfg.get("session.working_directory", ".")
        new_scope = canonical_todo_scope(raw)
        
        db_path = db_manager.get_project_db_path()
        query = 'UPDATE todos SET scope = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?'
        try:
            await db_manager.execute(db_path, query, (new_scope, node_id))
            # Reload all TodoTrees to reflect the move
            for tree in self.app.query("TodoTree"):
                tree.load_todos()
        except Exception as e:
            print(f"Failed to update scope: {e}")

    @work
    async def update_status(self, node_id: Any, status: str) -> None:
        db_path = db_manager.get_project_db_path()
        query = 'UPDATE todos SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?'
        try:
            await db_manager.execute(db_path, query, (status, node_id))
            self.load_todos()
        except Exception as e:
            print(f"Failed to update status: {e}")

    @work
    async def delete_todo(self, node_id: Any) -> None:
        db_path = db_manager.get_project_db_path()
        query = 'DELETE FROM todos WHERE id = ?'
        try:
            await db_manager.execute(db_path, query, (node_id,))
            self.load_todos()
        except Exception as e:
            print(f"Failed to delete todo: {e}")

    @work
    async def edit_todo(self, node_id: Any) -> None:
        db_path = db_manager.get_project_db_path()
        query = (
            "SELECT label, todo_text, deadline, completion_note, completion_date, comments "
            "FROM todos WHERE id = ?"
        )
        try:
            columns, rows = await db_manager.execute(db_path, query, (node_id,))
            if not rows:
                return

            r = rows[0]
            raw_comments = r[5] or "[]"
            try:
                comments_display = json.dumps(json.loads(raw_comments), indent=2)
            except (json.JSONDecodeError, TypeError):
                comments_display = raw_comments
            todo_data = {
                "label": r[0],
                "todo_text": r[1] or "",
                "deadline": r[2] or "",
                "completion_note": r[3] or "",
                "completion_date": r[4] or "",
                "comments": comments_display,
            }

            self._show_edit_modal(node_id, todo_data)
        except Exception as e:
            print(f"Failed to fetch todo for edit: {e}")

    def _show_edit_modal(self, node_id: Any, todo_data: dict) -> None:
        from components.utils.form_modal import FormModal
        
        schema = [
            {"key": "label", "label": "Label", "required": True},
            {"key": "todo_text", "label": "Details", "type": "textarea"},
            {"key": "deadline", "label": "Deadline (optional)"},
            {"key": "completion_note", "label": "Completion note (optional)", "type": "textarea"},
            {
                "key": "completion_date",
                "label": "Completion date (optional, e.g. YYYY-MM-DD)",
                "placeholder": "2025-03-20",
            },
            {
                "key": "comments",
                "label": "Comments (JSON array of strings)",
                "type": "code",
                "language": "json",
            },
        ]

        def on_save(values: dict):
            enc, err = todo_store.normalize_comments_json(values.get("comments") or "[]")
            if err:
                self.app.notify(err, severity="error")
                return
            values["comments"] = enc
            self.save_edit(node_id, values)

        modal = FormModal("Edit Todo", schema, args=todo_data, callback=on_save)
        self.app.push_screen(modal)

    @work
    async def save_edit(self, node_id: Any, values: dict) -> None:
        db_path = db_manager.get_project_db_path()
        query = """
            UPDATE todos
            SET label = ?, todo_text = ?, deadline = ?, completion_note = ?, completion_date = ?,
                comments = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """
        try:
            note = (values.get("completion_note") or "").strip() or None
            cdate = (values.get("completion_date") or "").strip() or None
            await db_manager.execute(
                db_path,
                query,
                (
                    values.get("label"),
                    values.get("todo_text"),
                    (values.get("deadline") or "").strip() or None,
                    note,
                    cdate,
                    values.get("comments") or "[]",
                    node_id,
                ),
            )
            self.load_todos()
        except Exception as e:
            print(f"Failed to save edit: {e}")
