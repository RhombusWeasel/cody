from textual.app import ComposeResult
from textual.containers import VerticalScroll, Vertical
from textual.widgets import Button, DataTable
from textual.message import Message
from textual import work, on

from utils.icons import DELETE
from utils.db import db_manager

CSS = """
#chat_list_table {
    height: auto;
}

#btn_new_chat {
    width: 100%;
    padding: 1 1;
}
#chat_list_table > .datatable--header {
    height: 1;
    color: $text-muted;
}

#chat_list_table .datatable--cursor {
    background: $primary 20%;
}
"""

class ChatHistoryTab(VerticalScroll):
    DEFAULT_CSS = CSS
    class ChatSelected(Message):
        def __init__(self, chat_id: str | None, title: str | None = None):
            self.chat_id = chat_id
            self.title = title
            super().__init__()

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Button("New Chat", id="btn_new_chat", variant="primary")
            yield DataTable(id="chat_list_table", cursor_type="cell")

    def on_mount(self) -> None:
        self.load_chats()

    @work
    async def load_chats(self) -> None:
        chats = await db_manager.get_chats()
        table = self.query_one("#chat_list_table", DataTable)
        table.clear(columns=True)
        table.add_columns(("Title", "title"), ("Updated", "updated"), ("Delete", "delete"))
        for chat in chats:
            title = chat["title"] or "Untitled Chat"
            updated = chat["updated_at"] or ""
            table.add_row(title, updated, DELETE, key=chat["id"])

    @on(Button.Pressed, "#btn_new_chat")
    def on_new_chat(self, event: Button.Pressed) -> None:
        self.post_message(self.ChatSelected(None))

    @on(DataTable.CellSelected, "#chat_list_table")
    async def on_cell_selected(self, event: DataTable.CellSelected) -> None:
        table = event.control
        cell_key = event.cell_key
        raw_key = cell_key[0] if isinstance(cell_key, tuple) else cell_key
        row_key = getattr(raw_key, "value", raw_key) or str(raw_key)
        cell_val = str(event.value).strip() if event.value else ""
        if DELETE in cell_val:
            event.stop()
            await db_manager.delete_chat(row_key)
            table.remove_row(raw_key)
        else:
            title_val = table.get_cell(raw_key, "title")
            self.post_message(self.ChatSelected(row_key, str(title_val) if title_val else None))
