from typing import Any
from textual.widgets import Button
from textual import work

from components.tree.generic_tree import GenericTree
from utils.tree_model import TreeEntry
from utils.db import db_manager

class TodoTree(GenericTree):
    """Tree view for displaying and managing todos for a specific scope."""

    def __init__(self, scope: str, **kwargs):
        super().__init__(**kwargs)
        self.scope = scope
        self._todos = []
        self._expanded.update(["pending", "completed"])

    def on_mount(self) -> None:
        super().on_mount()
        self.load_todos()

    @work
    async def load_todos(self) -> None:
        db_path = db_manager.get_project_db_path()
        query = 'SELECT id, label, status FROM todos WHERE scope = ? ORDER BY creation_time DESC'
        try:
            columns, rows = await db_manager.execute(db_path, query, (self.scope,))
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
        from utils.icons import CHECKED, UNCHECKED, FOLDER
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
        
        return [
            ActionButton(status_btn_label, action=lambda n=node_id, s=status_action: self.on_button_action(n, f"status_{s}"), tooltip=status_tooltip, classes="action-btn"),
            ActionButton(scope_btn_label, action=lambda n=node_id, s=scope_action: self.on_button_action(n, f"scope_{s}"), tooltip=scope_tooltip, classes="action-btn"),
            EditButton(action=lambda n=node_id: self.on_button_action(n, "edit")),
            DeleteButton(action=lambda n=node_id: self.on_button_action(n, "delete"))
        ]

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

    @work
    async def update_scope(self, node_id: Any, scope_type: str) -> None:
        from utils.cfg_man import cfg
        new_scope = "global" if scope_type == "global" else cfg.get('session.working_directory', '.')
        
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
        query = 'SELECT label, todo_text, deadline FROM todos WHERE id = ?'
        try:
            columns, rows = await db_manager.execute(db_path, query, (node_id,))
            if not rows:
                return
            
            r = rows[0]
            todo_data = {
                "label": r[0],
                "todo_text": r[1] or "",
                "deadline": r[2] or ""
            }
            
            self._show_edit_modal(node_id, todo_data)
        except Exception as e:
            print(f"Failed to fetch todo for edit: {e}")

    def _show_edit_modal(self, node_id: Any, todo_data: dict) -> None:
        from components.utils.form_modal import FormModal
        
        schema = [
            {"key": "label", "label": "Label", "required": True},
            {"key": "todo_text", "label": "Details", "type": "textarea"},
            {"key": "deadline", "label": "Deadline (optional)"}
        ]
        
        def on_save(values: dict):
            self.save_edit(node_id, values)
            
        modal = FormModal("Edit Todo", schema, args=todo_data, callback=on_save)
        self.app.push_screen(modal)

    @work
    async def save_edit(self, node_id: Any, values: dict) -> None:
        db_path = db_manager.get_project_db_path()
        query = '''
            UPDATE todos 
            SET label = ?, todo_text = ?, deadline = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        '''
        try:
            await db_manager.execute(db_path, query, (
                values.get("label"), 
                values.get("todo_text"), 
                values.get("deadline"), 
                node_id
            ))
            self.load_todos()
        except Exception as e:
            print(f"Failed to save edit: {e}")
