"""Streaming chat component — replaces MsgBox.get_agent_response with live token-by-token output.

Enabled via config: interface.streaming (default: True).
When disabled, the original blocking MsgBox.get_agent_response is used instead.
"""

import asyncio
import json
import uuid
from queue import Queue, Empty

from textual.reactive import reactive
from textual.containers import VerticalScroll, Vertical
from textual.widget import Widget
from textual.widgets import Markdown, Collapsible, LoadingIndicator, Label, Button, OptionList

from utils.agent import Agent
from utils.cfg_man import cfg
from utils.db import db_manager
from components.chat.input import MessageInput
from components.chat.message import Message
from components.utils.input_modal import InputModal

_MSG_INPUT_FOCUS_DELAY_SEC = 0.05


def _group_assistant_tool_messages(msgs: list, show_tool: bool = True) -> list:
    """Group assistant + tool messages until we hit an assistant with no tool_calls."""
    result = []
    i = 0
    while i < len(msgs):
        m = msgs[i]
        if m.get("role") == "system":
            result.append({
                "role": "system",
                "blocks": [{"type": "text", "content": m.get("content", ""), "loading": False}],
            })
            i += 1
        elif m.get("role") == "user":
            user_entry = {
                "role": "user",
                "blocks": [{"type": "text", "content": m.get("content", ""), "loading": False}],
            }
            if m.get("git_checkpoint"):
                user_entry["git_checkpoint"] = m["git_checkpoint"]
            result.append(user_entry)
            i += 1
        elif m.get("role") == "assistant":
            blocks = []
            while i < len(msgs):
                m = msgs[i]
                if m.get("role") == "assistant":
                    block = {"type": "text", "content": m.get("content", ""), "loading": False}
                    if m.get("thoughts"):
                        block["thoughts"] = m["thoughts"]
                    blocks.append(block)
                    i += 1
                    if not m.get("tool_calls"):
                        break
                elif m.get("role") == "tool":
                    if show_tool:
                        blocks.append({"type": "tool", "content": m.get("content", "")})
                    i += 1
                else:
                    break
            result.append({"role": "assistant", "blocks": blocks})
        else:
            i += 1
    return result


def _messages_to_display(messages: list, show_tool: bool = True) -> list:
    """Convert messages list to display format with blocks."""
    if not messages:
        return []
    last = messages[-1]
    if last.get("loading") or last.get("id"):
        grouped = _group_assistant_tool_messages(messages[:-1], show_tool)
        grouped.append({
            "role": "assistant",
            "blocks": [{"type": "text", "content": last.get("content", ""), "loading": True}],
        })
        return grouped
    return _group_assistant_tool_messages(messages, show_tool)


class StreamingMessage(Widget):
    """A single message widget that supports incremental content updates."""

    def __init__(self, role: str, blocks: list, git_checkpoint: str | None = None):
        super().__init__()
        self.role = role
        self.title = role
        self.border_title = role
        self.blocks = blocks
        self.git_checkpoint = git_checkpoint
        self.loading = any(b.get("loading") for b in blocks if b["type"] == "text")
        self._text_content = ""
        self._thoughts_content = None
        self._md_widget = None
        self._thoughts_md = None
        self._loading_indicator = None
        self._tool_widgets = []

    def compose(self):
        from components.utils.buttons import ActionButton
        with Collapsible(title=self.title, classes=self.title, collapsed=False):
            if self.role == "user" and self.git_checkpoint:
                short_hash = self.git_checkpoint[:7] if len(self.git_checkpoint) >= 7 else self.git_checkpoint
                yield ActionButton(f"Revert to here ({short_hash})", action=self.on_revert_pressed, id="revert_btn", variant="warning", classes="action-btn revert-btn")

            for block in self.blocks:
                if block["type"] == "text":
                    if block.get("thoughts"):
                        self._thoughts_content = block["thoughts"]
                    content = block.get("content", "")
                    if content:
                        self._text_content = content
                        md = Markdown(content)
                        md.code_indent_guides = False
                        self._md_widget = md
                        yield md
                    if block.get("loading"):
                        self._loading_indicator = LoadingIndicator()
                        yield self._loading_indicator
                elif block["type"] == "tool":
                    w = self._make_tool_widget(block["content"])
                    if w:
                        self._tool_widgets.append(w)
                        yield w

            if self._thoughts_content:
                with Collapsible(title="\U0001f4ad Agent Thoughts", classes="thoughts", collapsed=False):
                    md = Markdown(self._thoughts_content)
                    md.code_indent_guides = False
                    self._thoughts_md = md
                    yield md

    def _make_tool_widget(self, content: str):
        """Create a collapsible tool widget from tool JSON content."""
        try:
            data = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            md = Markdown(content)
            md.code_indent_guides = False
            return md

        func = data.get("function", "unknown_tool")
        args = data.get("arguments", {})
        result = data.get("result", "")

        # Format args as a markdown table
        parts = []
        if args:
            rows = ["| Argument | Value |", "| --- | --- |"]
            for k, v in args.items():
                val = str(v) if not isinstance(v, (dict, list)) else json.dumps(v)
                val = val.replace("|", "\\|").replace("\n", " ")
                rows.append(f"| {k} | {val} |")
            parts.append("\n".join(rows))
        if result:
            if not isinstance(result, str):
                result = json.dumps(result, indent=2)
            parts.append(f"**Result:**\n\n```\n{result}\n```")
        content_md = "\n\n".join(parts) or "(no output)"

        is_standalone = self.role == "tool" and len(self.blocks) == 1
        with Collapsible(title=func, classes="tool", collapsed=not is_standalone):
            md = Markdown(content_md)
            md.code_indent_guides = False
            return md

    def append_content(self, delta: str):
        """Append text content to the message and update the Markdown widget in-place."""
        if not delta:
            return
        self._text_content += delta
        if self._md_widget is not None:
            try:
                self._md_widget.update(self._text_content)
            except Exception:
                pass

    def append_thoughts(self, delta: str):
        """Append thoughts/reasoning content."""
        if not delta:
            return
        if self._thoughts_content is None:
            self._thoughts_content = ""
        self._thoughts_content += delta
        if self._thoughts_md is not None:
            try:
                self._thoughts_md.update(self._thoughts_content)
            except Exception:
                pass

    def add_tool_block(self, content: str):
        """Add a tool block to this message."""
        w = self._make_tool_widget(content)
        if w:
            self._tool_widgets.append(w)
            # Mount the new widget into the collapsible
            try:
                collapsible = self.query_one(Collapsible)
                collapsible.mount(w)
            except Exception:
                pass

    def finalize(self):
        """Remove loading indicator and mark as complete."""
        self.loading = False
        if self._loading_indicator is not None:
            try:
                self._loading_indicator.remove()
            except Exception:
                pass
            self._loading_indicator = None

    def on_revert_pressed(self) -> None:
        if not self.git_checkpoint:
            return
        from components.utils.input_modal import InputModal
        from components.chat.chat import MsgBox
        from components.chat.input import MessageInput
        from utils.cfg_man import cfg
        from utils.git import revert_to_checkpoint
        import asyncio
        wd = cfg.get("session.working_directory")
        commit_hash = self.git_checkpoint
        content = self.blocks[0].get("content", "") if self.blocks else ""
        raw_query = content.split("\n\n`")[0].strip() if "\n\n`" in content else content
        node = self.parent
        msg_box = None
        while node:
            if isinstance(node, StreamingMsgBox):
                msg_box = node
                break
            node = getattr(node, "parent", None)

        def on_confirm(confirmed: bool | None) -> None:
            if not confirmed or not msg_box:
                return

            async def _do_revert() -> None:
                await asyncio.to_thread(revert_to_checkpoint, wd, commit_hash)
                idx = None
                for i, m in enumerate(msg_box.actor.msg):
                    if m.get("git_checkpoint") == commit_hash:
                        idx = i
                        break
                if idx is None:
                    return
                msg_box.actor.msg = msg_box.actor.msg[:idx]
                show_system = msg_box.config.get("interface.show_system_messages", False)
                msg_box.messages = msg_box.actor.msg if show_system else [m for m in msg_box.actor.msg if m.get("role") != "system"]
                try:
                    inp = msg_box.query_one(MessageInput)
                    inp.value = raw_query
                except Exception:
                    pass
                await msg_box.save_chat()
                msg_box._refresh_chat_history()

            self.app.run_worker(_do_revert())

        self.app.push_screen(
            InputModal("Revert working tree to this checkpoint? This will overwrite uncommitted changes.", confirm_only=True),
            on_confirm,
        )


class StreamingMsgBox(Widget):
    """A chat message box that streams responses token-by-token."""

    messages = reactive([])

    def __init__(self, actor, config, chat_id: str, db_path: str | None = None, **kwargs):
        self.actor = actor
        self.config = config
        self.chat_id = chat_id
        self.db_path = db_path
        self.chat_title = "New Chat"
        self._abort_event = asyncio.Event()
        super().__init__(id=f"chat_box-{chat_id}", classes="msgbox", **kwargs)
        show_system = config.get("interface.show_system_messages", False)
        self.messages = actor.msg if show_system else [m for m in actor.msg if m.get("role") != "system"]

    def compose(self):
        with Vertical():
            yield VerticalScroll(id="msg_scroll", classes="chat")
            with Vertical(classes="container"):
                yield Label(id=f"usage_{self.chat_id}", classes="usage-bar")
                yield MessageInput(self.actor, self.chat_id, db_path=self.db_path, classes="msginput")
                yield OptionList(id=f"autocomplete_{self.chat_id}", classes="autocomplete-list")

    def watch_messages(self, messages: list) -> None:
        try:
            scroll = self.query_one("#msg_scroll", VerticalScroll)
        except Exception:
            return
        scroll.remove_children()
        show_tool = self.config.get("interface.show_tool_messages", True)
        for msg in _messages_to_display(messages, show_tool):
            role = msg.get("role", "user")
            blocks = msg.get("blocks", [])
            git_checkpoint = msg.get("git_checkpoint")
            scroll.mount(StreamingMessage(role, blocks, git_checkpoint=git_checkpoint))
        scroll.scroll_end()
        self._update_usage_display()

    def _update_usage_display(self) -> None:
        try:
            label = self.query_one(f"#usage_{self.chat_id}", Label)
        except Exception:
            return
        usage = getattr(self.actor, 'total_usage', None)
        if usage and usage.prompt_tokens > 0:
            pct = usage.context_used_pct
            if usage.context_window > 0:
                label.update(
                    f"Context: {usage.prompt_tokens:,} / {usage.context_window:,} ({pct}%)"
                )
            else:
                label.update(
                    f"Prompt tokens: {usage.prompt_tokens:,}"
                )
            label.styles.display = "block"
        else:
            label.styles.display = "none"

    def on_mount(self) -> None:
        self.watch_messages(self.messages)
        self.set_timer(_MSG_INPUT_FOCUS_DELAY_SEC, self._focus_message_input)

    def _focus_message_input(self) -> None:
        try:
            inp = self.query_one(MessageInput)
        except Exception:
            return
        if inp.is_mounted:
            inp.focus()

    def abort_agent_response(self) -> None:
        """Set the abort flag so streaming stops at the next check point."""
        self._abort_event.set()

    async def get_agent_response(self, user_text: str, placeholder_id: str, git_checkpoint: str | None = None) -> None:
        """Stream a response from the agent, updating the UI incrementally."""
        from utils.tool import execute_tool
        from utils.providers.openai_vault import ensure_openai_api_key_for_tui
        from utils.providers.ollama_vault import ensure_ollama_api_key_for_tui

        self._abort_event.clear()
        len_before = len(self.actor.msg)

        if cfg.get("session.provider", "").lower() == "openai":
            if not await ensure_openai_api_key_for_tui(self.app):
                await self._abort_agent_response(user_text, placeholder_id, git_checkpoint, len_before)
                return

        if cfg.get("session.provider", "").lower() == "ollama":
            if not await ensure_ollama_api_key_for_tui(self.app):
                await self._abort_agent_response(user_text, placeholder_id, git_checkpoint, len_before)
                return

        user_msg = {"role": "user", "content": user_text}
        if git_checkpoint:
            user_msg["git_checkpoint"] = git_checkpoint
        self.actor.msg.append(user_msg)
        base_messages = [dict(m) for m in self.messages if m.get("id") != placeholder_id]

        # Show the placeholder "Thinking..." message
        self._sync_messages(len_before, placeholder_id, base_messages, pending_loading=True)

        try:
            stream = self.actor.get_response_stream("")
        except Exception as e:
            from openai import AuthenticationError
            from ollama import ResponseError

            if isinstance(e, AuthenticationError) and cfg.get("session.provider", "").lower() == "openai":
                from utils.providers.openai_vault import clear_openai_api_key_cache
                clear_openai_api_key_cache()
                self.actor.add_msg("assistant", "OpenAI authentication failed (invalid or expired API key). Fix providers.openai.api_key in settings, add a key in the Password Vault, or set OPENAI_API_KEY in the environment.")
            elif isinstance(e, ResponseError) and getattr(e, "status_code", None) in (401, 403) and cfg.get("session.provider", "").lower() == "ollama":
                from utils.providers.ollama_vault import clear_ollama_api_key_cache
                clear_ollama_api_key_cache()
                self.actor.add_msg("assistant", "Ollama authentication failed (invalid or expired API key). Fix providers.ollama.api_key, add a key in the Password Vault (providers / Ollama API Key), or set OLLAMA_API_KEY.")
            else:
                raise

            self._sync_messages(len_before, placeholder_id, base_messages, pending_loading=False)
            await self.save_chat()
            self._refresh_chat_history()
            return

        # Get the last message widget (the placeholder) for incremental updates
        scroll = self.query_one("#msg_scroll", VerticalScroll)
        last_msg = None
        try:
            children = list(scroll.children)
            if children:
                last_msg = children[-1]
        except Exception:
            pass

        # Use a queue to bridge sync stream consumer -> async UI updates
        chunk_queue: Queue = Queue()
        sentinel = object()

        def _consume_stream():
            """Run in a thread — feeds chunks into the queue.
            Do NOT break on chunk.done — the generator needs to run to
            completion so get_response_stream can record the assistant
            message in self.actor.msg via add_msg() after the yield.
            """
            try:
                for chunk in stream:
                    chunk_queue.put(chunk)
            except Exception as exc:
                chunk_queue.put(exc)
            finally:
                chunk_queue.put(sentinel)

        # Start the consumer in a thread
        consume_task = asyncio.get_running_loop().run_in_executor(None, _consume_stream)

        # Read from the queue on the async side, yielding to the event loop
        while True:
            try:
                item = chunk_queue.get(timeout=0.05)
            except Empty:
                if self._abort_event.is_set():
                    break
                continue

            if item is sentinel:
                break
            if isinstance(item, Exception):
                raise item

            chunk = item

            if chunk.content:
                if last_msg is not None and hasattr(last_msg, 'append_content'):
                    last_msg.append_content(chunk.content)
                    scroll.scroll_end(animate=False)

            if chunk.thoughts:
                if last_msg is not None and hasattr(last_msg, 'append_thoughts'):
                    last_msg.append_thoughts(chunk.thoughts)

            if chunk.tool_calls:
                # Execute tool calls and show results
                for tc in chunk.tool_calls:
                    if self._abort_event.is_set():
                        break
                    args = tc.function.arguments or {}
                    if isinstance(args, str):
                        args = json.loads(args) if args else {}
                    if tc.function.name == "run_command":
                        command = args.get("command", "")
                        loop = asyncio.get_running_loop()
                        future = loop.create_future()

                        def on_confirm(ok: bool | None):
                            loop.call_soon_threadsafe(future.set_result, ok)

                        self.app.push_screen(
                            InputModal(f"Run command?\n\n{command}", confirm_only=True),
                            on_confirm
                        )
                        confirmed = await future
                        if not confirmed:
                            result = "User cancelled."
                        else:
                            result = await asyncio.to_thread(execute_tool, tc.function.name, args)
                    else:
                        result = await asyncio.to_thread(execute_tool, tc.function.name, args)

                    if not isinstance(result, str):
                        result = json.dumps(result)
                    tool_data = json.dumps({
                        "function": tc.function.name,
                        "arguments": args,
                        "result": result,
                    })
                    self.actor.add_msg("tool", tool_data, tool_call_id=getattr(tc, "id", None) or "")

                    # Add tool block to the current message
                    if last_msg is not None and hasattr(last_msg, 'add_tool_block'):
                        last_msg.add_tool_block(tool_data)
                        scroll.scroll_end(animate=False)

            if chunk.done:
                # Finalize the message
                if last_msg is not None and hasattr(last_msg, 'finalize'):
                    last_msg.finalize()

        # Ensure the thread is cleaned up
        await consume_task

        if self._abort_event.is_set():
            self.actor.add_msg("assistant", "Cancelled by user.")
            self._sync_messages(len_before, placeholder_id, base_messages, pending_loading=False)
        else:
            self._sync_messages(len_before, placeholder_id, base_messages, pending_loading=False)

        await self.save_chat()
        self._refresh_chat_history()

    async def _abort_agent_response(self, user_text, placeholder_id, git_checkpoint, len_before):
        """Handle aborted response due to missing API key."""
        user_msg = {"role": "user", "content": user_text}
        if git_checkpoint:
            user_msg["git_checkpoint"] = git_checkpoint
        self.actor.msg.append(user_msg)
        provider = cfg.get("session.provider", "").lower()
        if provider == "openai":
            msg = "OpenAI setup was cancelled or failed. Unlock the password vault and add an API key, or set providers.openai.api_key in settings."
        else:
            msg = "Ollama Cloud setup was cancelled or failed. Unlock the password vault and add an API key under providers / Ollama API Key, set providers.ollama.api_key in settings, or set OLLAMA_API_KEY."
        self.actor.add_msg("assistant", msg)
        base_messages = [dict(m) for m in self.messages if m.get("id") != placeholder_id]
        self._sync_messages(len_before, placeholder_id, base_messages, pending_loading=False)
        await self.save_chat()
        self._refresh_chat_history()

    def _sync_messages(self, len_before, placeholder_id, base_messages, *, pending_loading):
        """Rebuild this turn from actor.msg."""
        show_system = self.config.get("interface.show_system_messages", False)
        displayable = (
            self.actor.msg if show_system else [m for m in self.actor.msg if m.get("role") != "system"]
        )
        len_before_displayable = len(
            [m for m in self.actor.msg[:len_before] if show_system or m.get("role") != "system"]
        )
        tail = displayable[len_before_displayable:]
        new_to_show = [dict(m) for m in tail[1:]]
        out = [dict(m) for m in base_messages] + new_to_show
        if pending_loading:
            out = out + [
                {
                    "id": placeholder_id,
                    "role": "assistant",
                    "content": "Thinking\u2026",
                    "loading": True,
                }
            ]
        self.messages = out

    def _refresh_chat_history(self) -> None:
        try:
            from components.sidebar.chat_history import ChatHistoryTab
            chat_history = self.app.query_one(ChatHistoryTab)
            chat_history.load_chats()
        except Exception:
            pass

    async def save_chat(self) -> None:
        title = getattr(self, "chat_title", "New Chat")
        if self.db_path is not None:
            import json
            from utils.db_providers import SqliteDbProvider
            serialized = [dict(m) for m in self.actor.msg]
            prov = SqliteDbProvider(self.db_path)
            try:
                conn = prov.sqlite_connection
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS chats (
                        id TEXT PRIMARY KEY,
                        title TEXT,
                        chat_data TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute(
                    "INSERT INTO chats (id, title, chat_data, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP) "
                    "ON CONFLICT(id) DO UPDATE SET title=excluded.title, chat_data=excluded.chat_data, updated_at=CURRENT_TIMESTAMP",
                    (self.chat_id, title, json.dumps(serialized))
                )
                conn.commit()
            finally:
                prov.close()
        else:
            await db_manager.save_chat(self.chat_id, title, self.actor.msg)