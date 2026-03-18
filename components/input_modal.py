from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Label, Input, Button, TextArea
from textual.screen import ModalScreen
from textual import on

class InputModal(ModalScreen):


    def __init__(self, title: str, initial_value: str = "", multiline: bool = False, language: str | None = None, code_editor: bool = False, confirm_only: bool = False):
        super().__init__()
        self.title_text = title
        self.initial_value = initial_value
        self.multiline = multiline
        self.language = language
        self.code_editor = code_editor
        self.confirm_only = confirm_only

    def compose(self) -> ComposeResult:
        with Vertical(id="input_modal_container"):
            yield Label(self.title_text)
            if not self.confirm_only:
                if self.code_editor and self.language:
                    yield TextArea.code_editor(self.initial_value, id="input_modal_input", language=self.language)
                elif self.multiline:
                    yield TextArea(self.initial_value, id="input_modal_input", language=self.language)
                else:
                    yield Input(self.initial_value, id="input_modal_input")
            with Horizontal(classes="modal-button-container"):
                if self.confirm_only:
                    yield Button("Confirm", id="btn_input_modal_save", variant="primary", classes="modal-button")
                else:
                    yield Button("Save", id="btn_input_modal_save", variant="primary", classes="modal-button")
                yield Button("Cancel", id="btn_input_modal_cancel", variant="error", classes="modal-button")

    def on_mount(self) -> None:
        if self.confirm_only:
            return
        if self.language == "lua" and (self.code_editor or self.multiline):
            try:
                import tree_sitter_lua
                from tree_sitter import Language
                from pathlib import Path
                
                text_area = self.query_one("#input_modal_input", TextArea)
                lua_lang = Language(tree_sitter_lua.language())
                highlights_path = Path(tree_sitter_lua.__file__).parent / "queries" / "highlights.scm"
                highlights = highlights_path.read_text()
                
                text_area.register_language("lua", lua_lang, highlights)
                # Force reload of the document to apply the new language registration
                text_area.language = ""
                text_area.language = "lua"
            except ImportError:
                pass

    @on(Button.Pressed, "#btn_input_modal_save")
    def on_save(self) -> None:
        if self.confirm_only:
            self.dismiss(True)
        elif self.multiline:
            val = self.query_one("#input_modal_input", TextArea).text
            self.dismiss(val)
        else:
            val = self.query_one("#input_modal_input", Input).value
            self.dismiss(val)

    @on(Button.Pressed, "#btn_input_modal_cancel")
    def on_cancel(self) -> None:
        self.dismiss(None)
