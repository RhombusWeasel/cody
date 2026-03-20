from textual.app import ComposeResult
from textual.containers import VerticalScroll, Vertical, Horizontal
from textual.widgets import Button, Label
from textual.message import Message
from textual.events import Click
from textual import work, on

from utils.icons import DELETE
from utils.db import db_manager


class ChatItem(Horizontal):
    class Selected(Message):
        def __init__(self, chat_id: str, title: str):
            self.chat_id = chat_id
            self.title = title
            super().__init__()

    class Delete(Message):
        def __init__(self, chat_id: str):
            self.chat_id = chat_id
            super().__init__()

    def __init__(self, chat_id: str, title: str, updated: str):
        super().__init__(classes="chat-item")
        self.chat_id = chat_id
        self.chat_title = title
        self.updated = updated

    def compose(self) -> ComposeResult:
        from components.utils.buttons import DeleteButton
        yield Label(self.chat_title, classes="chat-item-title")
        yield Label(self.updated, classes="chat-item-updated")
        yield DeleteButton(action=lambda: self.post_message(self.Delete(self.chat_id)), classes="action-btn")

    async def on_click(self, event: Click) -> None:
        self.post_message(self.Selected(self.chat_id, self.chat_title))


class ChatHistoryTab(VerticalScroll):
    class ChatSelected(Message):
        def __init__(self, chat_id: str | None, title: str | None = None):
            self.chat_id = chat_id
            self.title = title
            super().__init__()

    def compose(self) -> ComposeResult:
        from components.utils.buttons import AddButton
        with Vertical():
            yield AddButton(action=self.on_new_chat, label="New Chat", id="btn_new_chat")
            yield Vertical(id="chat_list_container")

    def on_mount(self) -> None:
        self.load_chats()

    @work
    async def load_chats(self) -> None:
        chats = await db_manager.get_chats()
        container = self.query_one("#chat_list_container", Vertical)
        await container.remove_children()
        
        for chat in chats:
            title = chat["title"] or "Untitled Chat"
            updated = chat["updated_at"] or ""
            chat_id = str(chat["id"])
            await container.mount(ChatItem(chat_id, title, updated))

    def on_new_chat(self) -> None:
        self.post_message(self.ChatSelected(None))

    @on(ChatItem.Selected)
    def on_chat_selected(self, event: ChatItem.Selected) -> None:
        self.post_message(self.ChatSelected(event.chat_id, event.title))

    @on(ChatItem.Delete)
    async def on_chat_delete(self, event: ChatItem.Delete) -> None:
        await db_manager.delete_chat(event.chat_id)
        for item in self.query(ChatItem):
            if item.chat_id == event.chat_id:
                item.remove()
                break
