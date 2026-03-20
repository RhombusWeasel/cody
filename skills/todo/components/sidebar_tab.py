from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Label, Button
from textual import work

from utils.cfg_man import cfg
from utils.db import db_manager
from utils.paths import canonical_todo_scope
from components.utils.buttons import AddButton
from skills.todo.components.todo_tree import TodoTree
from skills.todo.scripts import todo_store

sidebar_label = "󱛡"
sidebar_tooltip = "Manage Todos"

class TodoSidebarTab(Vertical):
    """Sidebar tab for managing global and local todos."""

    def compose(self) -> ComposeResult:
        from utils.icons import FOLDER
        with Vertical(classes="todo-section"):
            with Horizontal(classes="todo-header"):
                yield Label(f" Global Todos", classes="todo-title")
                yield AddButton(action=lambda: self.add_todo("global"), tooltip="Add Global Todo")
            yield TodoTree(scope="global", id="global_todo_tree")

        with Vertical(classes="todo-section"):
            with Horizontal(classes="todo-header"):
                yield Label(f"{FOLDER} Local Todos", classes="todo-title")
                working_dir = canonical_todo_scope(cfg.get("session.working_directory", "."))
                yield AddButton(action=lambda w=working_dir: self.add_todo(w), tooltip="Add Local Todo")
            yield TodoTree(scope=working_dir, id="local_todo_tree")

    def add_todo(self, scope: str) -> None:
        from components.utils.form_modal import FormModal
        
        schema = [
            {"key": "label", "label": "Label", "required": True},
            {"key": "todo_text", "label": "Details", "type": "textarea"},
            {"key": "deadline", "label": "Deadline (optional)"},
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
            self.save_new_todo(scope, values)

        modal = FormModal(
            f"Add {'Global' if scope == 'global' else 'Local'} Todo",
            schema,
            args={"comments": "[]"},
            callback=on_save,
        )
        self.app.push_screen(modal)

    @work
    async def save_new_todo(self, scope: str, values: dict) -> None:
        db_path = db_manager.get_project_db_path()
        query = '''
            INSERT INTO todos (label, scope, todo_text, deadline, comments)
            VALUES (?, ?, ?, ?, ?)
        '''
        try:
            await db_manager.execute(
                db_path,
                query,
                (
                    values.get("label"),
                    scope,
                    values.get("todo_text"),
                    values.get("deadline") or None,
                    values.get("comments") or "[]",
                ),
            )
            
            # Reload the appropriate tree
            tree_id = "#global_todo_tree" if scope == "global" else "#local_todo_tree"
            tree = self.query_one(tree_id, TodoTree)
            tree.load_todos()
        except Exception as e:
            print(f"Failed to add new todo: {e}")

def get_sidebar_widget():
    return TodoSidebarTab()
