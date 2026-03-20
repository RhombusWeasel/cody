import pyte
from rich.text import Text
from textual import events
from textual.containers import VerticalScroll
from textual.widgets import Label, Button
from textual_terminal import Terminal
from textual_terminal._terminal import TerminalDisplay

class CustomTerminalPyteScreen(pyte.HistoryScreen):
    def set_margins(self, *args, **kwargs):
        kwargs.pop("private", None)
        return super().set_margins(*args, **kwargs)

    def resize(self, lines: int | None = None, columns: int | None = None) -> None:
        lines = lines or self.lines
        columns = columns or self.columns

        if lines == self.lines and columns == self.columns:
            return

        self.dirty.update(range(lines))

        if lines < self.lines:
            shift_count = max(0, self.cursor.y - (lines - 1))
            
            if shift_count > 0:
                for y in range(shift_count):
                    if y in self.buffer:
                        self.history.top.append(self.buffer[y].copy())
                        if len(self.history.top) > self.history.ratio:
                            self.history.top.popleft()
                
                new_buffer = {}
                for y in range(shift_count, self.lines):
                    if y in self.buffer:
                        new_buffer[y - shift_count] = self.buffer[y]
                self.buffer = new_buffer
                
                self.cursor.y -= shift_count
                
            for y in list(self.buffer.keys()):
                if y >= lines:
                    del self.buffer[y]
            
        elif lines > self.lines:
            pull_count = min(lines - self.lines, len(self.history.top))
            
            if pull_count > 0:
                new_buffer = {}
                for y in range(self.lines):
                    if y in self.buffer:
                        new_buffer[y + pull_count] = self.buffer[y]
                self.buffer = new_buffer
                
                for y in range(pull_count - 1, -1, -1):
                    self.buffer[y] = self.history.top.pop()
                    
                self.cursor.y += pull_count

        if columns < self.columns:
            for line in self.buffer.values():
                for x in range(columns, self.columns):
                    line.pop(x, None)

        self.lines, self.columns = lines, columns
        self.set_margins()

class CustomTerminal(Terminal):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Replace screen with HistoryScreen for scrollback
        self._screen = CustomTerminalPyteScreen(self.ncol, self.nrow, history=10000)
        self.stream = pyte.Stream(self._screen)
        self._term_scroll_offset = 0
        
        # Add missing key bindings
        self.ctrl_keys.update({
            "enter": "\r",
            "backspace": "\x7f",
            "tab": "\t",
            "escape": "\x1b",
            "space": " ",
        })
        # Add ctrl+a through ctrl+z
        for i, char in enumerate("abcdefghijklmnopqrstuvwxyz", 1):
            self.ctrl_keys[f"ctrl+{char}"] = chr(i)

    async def on_resize(self, event: events.Resize) -> None:
        if self.emulator is None:
            return
        
        # Only resize if the size actually changed to avoid unnecessary screen clears
        if self.ncol == self.size.width and self.nrow == self.size.height:
            return
            
        self.ncol = self.size.width
        self.nrow = self.size.height
        await self.send_queue.put(["set_size", self.nrow, self.ncol])
        self._screen.resize(self.nrow, self.ncol)

    async def on_key(self, event: events.Key) -> None:
        # Terminal consumes keys before app BINDINGS run; mirror AppShellKeybindsMixin
        # (ctrl+grave_accent / ctrl+t) plus send-to-chat (ctrl+i).
        if event.key in ["ctrl+i", "ctrl+t", "ctrl+grave_accent"]:
            if event.key == "ctrl+i":
                self.app.action_send_terminal_to_chat()
            elif event.key == "ctrl+t":
                self.app.action_toggle_visible("term-sidebar")
            elif event.key == "ctrl+grave_accent":
                self.app.action_toggle_visible("util-sidebar")
            event.prevent_default()
            event.stop()
            return
            
        self._term_scroll_offset = 0

    async def on_mouse_scroll_up(self, event: events.MouseScrollUp):
        if self.emulator is None:
            return
        if not self.mouse_tracking:
            self._term_scroll_offset += 3
            max_scroll = len(self._screen.history.top)
            self._term_scroll_offset = min(self._term_scroll_offset, max_scroll)
            self.refresh()

    async def on_mouse_scroll_down(self, event: events.MouseScrollDown):
        if self.emulator is None:
            return
        if not self.mouse_tracking:
            self._term_scroll_offset -= 3
            self._term_scroll_offset = max(0, self._term_scroll_offset)
            self.refresh()

    def render(self):
        if not hasattr(self, '_screen') or not hasattr(self._screen, 'history'):
            return super().render()

        lines = []
        history = list(self._screen.history.top)
        buffer_lines = [self._screen.buffer[y] for y in range(self._screen.lines)]
        
        all_lines = history + buffer_lines
        
        start_idx = len(all_lines) - self._screen.lines - self._term_scroll_offset
        start_idx = max(0, start_idx)
        
        visible_lines = all_lines[start_idx : start_idx + self._screen.lines]
        
        for y, line in enumerate(visible_lines):
            line_text = Text()
            style_change_pos = 0
            for x in range(self._screen.columns):
                char = line[x]
                line_text.append(char.data)
                if x > 0:
                    last_char = line[x - 1]
                    if not self.char_style_cmp(char, last_char):
                        last_style = self.char_rich_style(last_char)
                        if last_style:
                            line_text.stylize(last_style, style_change_pos, x)
                        style_change_pos = x
                        
                # Show cursor only if we are at the bottom (not scrolled up)
                if self._term_scroll_offset == 0 and self._screen.cursor.x == x and self._screen.cursor.y == y:
                    line_text.stylize("reverse", x, x + 1)
                    
            # At the end of the line, stylize the remaining characters
            if self._screen.columns > 0:
                last_style = self.char_rich_style(line[self._screen.columns - 1])
                if last_style:
                    line_text.stylize(last_style, style_change_pos, self._screen.columns)
                    
            lines.append(line_text)
            
        return TerminalDisplay(lines)

    def get_all_text(self) -> str:
        if not hasattr(self, '_screen') or not hasattr(self._screen, 'history'):
            return ""
        
        history = list(self._screen.history.top)
        buffer_lines = [self._screen.buffer[y] for y in range(self._screen.lines)]
        all_lines = history + buffer_lines
        
        text_lines = []
        for line in all_lines:
            line_str = "".join(line[x].data for x in range(self._screen.columns))
            text_lines.append(line_str.rstrip())
            
        while text_lines and not text_lines[-1]:
            text_lines.pop()
            
        return "\n".join(text_lines)

class TerminalSidebar(VerticalScroll):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._custom_bindings = [
            ('ctrl+i', 'send_terminal_to_chat', 'Send Terminal to Chat'),
        ]

    def compose(self):
        from components.utils.buttons import ActionButton
        yield ActionButton("Send to Chat", action=self.app.on_send_terminal_chat, id="btn_send_terminal_chat", variant="primary", classes="action-btn")
        yield CustomTerminal(command="bash", id="terminal_bash")

    def on_mount(self) -> None:
        # We start the terminal when it is first shown to avoid 0-width initialization issues
        pass

    def start_terminal(self) -> None:
        if not getattr(self, '_terminal_started', False):
            self._terminal_started = True
            terminal = self.query_one("#terminal_bash", CustomTerminal)
            terminal.start()
