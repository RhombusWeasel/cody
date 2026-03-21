import uuid
from pathlib import Path
from typing import Callable

from textual.app import ComposeResult
from textual.widgets import TabPane, TextArea
from textual.binding import Binding

class EditorTab(TabPane):
    BINDINGS = [
        Binding("ctrl+s", "save_file", "Save File", show=True)
    ]

    def __init__(self, path: Path, content: str, language: str | None = None, code_editor: bool = False, on_saved: Callable[[], None] | None = None, **kwargs):
        self.file_path = path
        self.initial_content = content
        self.language = language
        self.code_editor = code_editor
        self.on_saved = on_saved
        self.tab_id = str(uuid.uuid1())
        super().__init__(path.name, id=f"editor-{self.tab_id}", **kwargs)

    def compose(self) -> ComposeResult:
        if self.code_editor and self.language:
            yield TextArea.code_editor(self.initial_content, id="editor_textarea", language=self.language)
        else:
            yield TextArea(self.initial_content, id="editor_textarea", language=self.language)

    def on_mount(self) -> None:
        if self.language == "lua":
            try:
                import tree_sitter_lua
                from tree_sitter import Language
                from pathlib import Path as PPath

                text_area = self.query_one("#editor_textarea", TextArea)
                lua_lang = Language(tree_sitter_lua.language())
                highlights_path = PPath(tree_sitter_lua.__file__).parent / "queries" / "highlights.scm"
                highlights = highlights_path.read_text()

                text_area.register_language("lua", lua_lang, highlights)
                text_area.language = ""
                text_area.language = "lua"
            except ImportError:
                pass

    def action_save_file(self) -> None:
        text_area = self.query_one("#editor_textarea", TextArea)
        try:
            self.file_path.write_text(text_area.text, encoding="utf-8")
            self.app.notify(f"Saved {self.file_path.name}")
            if self.on_saved:
                self.on_saved()
        except Exception as e:
            self.app.notify(f"Error saving: {e}", severity="error")
