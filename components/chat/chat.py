import asyncio
from textual.reactive import reactive
from textual.containers import VerticalScroll, Vertical
from textual.widget import Widget
from textual.widgets import TabbedContent, TabPane, OptionList
from utils.agent import Agent
from utils.cfg_man import cfg
from utils.db import db_manager
import uuid
import json



from components.chat.input import MessageInput
from components.chat.message import Message
from components.utils.input_modal import InputModal


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
          if m.get("content"):
            blocks.append({"type": "text", "content": m["content"], "loading": False})
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
  """Convert messages list to display format with blocks. Handles placeholders and agent format."""
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


class MsgBox(Widget):
  messages = reactive([])

  def __init__(self, actor, config, chat_id: str, **kwargs):
    self.actor = actor
    self.config = config
    self.chat_id = chat_id
    self.chat_title = "New Chat"
    super().__init__(id=f"chat_box-{chat_id}", classes="msgbox", **kwargs)
    show_system = config.get("interface.show_system_messages", False)
    self.messages = actor.msg if show_system else [m for m in actor.msg if m.get("role") != "system"]

  def compose(self):
    with Vertical():
      yield VerticalScroll(id="msg_scroll", classes="chat")
      with Vertical(classes="container"):
        yield MessageInput(self.actor, self.chat_id, classes="msginput")
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
      scroll.mount(Message(role, blocks, git_checkpoint=git_checkpoint))
    scroll.scroll_end()

  def on_mount(self) -> None:
    self.watch_messages(self.messages)

  async def get_agent_response(self, user_text: str, placeholder_id: str, git_checkpoint: str | None = None) -> None:
    from utils.tool import execute_tool

    len_before = len(self.actor.msg)

    user_msg = {"role": "user", "content": user_text}
    if git_checkpoint:
      user_msg["git_checkpoint"] = git_checkpoint
    self.actor.msg.append(user_msg)

    while True:
      resp = await asyncio.to_thread(self.actor.get_response, "")
      if not resp.message.tool_calls:
        break
      for tc in resp.message.tool_calls:
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
    pre = [m for m in self.messages if m.get("id") != placeholder_id]
    show_system = self.config.get("interface.show_system_messages", False)
    displayable = self.actor.msg if show_system else [m for m in self.actor.msg if m.get("role") != "system"]
    len_before_displayable = len([m for m in self.actor.msg[:len_before] if show_system or m.get("role") != "system"])
    new_from_agent = displayable[len_before_displayable:]
    new_to_show = [dict(m) for m in new_from_agent[1:]]
    self.messages = pre + new_to_show

    await self.save_chat()
    self._refresh_chat_history()

  def _refresh_chat_history(self) -> None:
    try:
      from components.sidebar.chat_history import ChatHistoryTab
      chat_history = self.app.query_one(ChatHistoryTab)
      chat_history.load_chats()
    except Exception:
      pass

  async def save_chat(self) -> None:
    title = getattr(self, "chat_title", "New Chat")
    await db_manager.save_chat(self.chat_id, title, self.actor.msg)


class Chat(Widget):
    def __init__(self, config, **kwargs):
        self.config = config
        super().__init__(**kwargs)

    def compose(self):
        yield TabbedContent(id="chat_tabs")

    async def on_mount(self):
        await self.add_chat_tab()

    async def add_chat_tab(self, chat_id=None, chat_data=None, title=None):
        tabs = self.query_one("#chat_tabs", TabbedContent)
        
        if chat_id:
            for tab in tabs.query(TabPane):
                if tab.id == f"tab-{chat_id}":
                    tabs.active = f"tab-{chat_id}"
                    return

        new_chat_id = chat_id or str(uuid.uuid1())
        actor = Agent()
        if chat_data:
            actor.msg = chat_data
            
        if not title:
            title = "New Chat"
            if chat_data:
                for msg in chat_data:
                    if msg['role'] == 'user':
                        title = msg['content'][:30] + "..." if len(msg['content']) > 30 else msg['content']
                        break

        msg_box = MsgBox(actor, self.config, chat_id=new_chat_id)
        if chat_data and title != "New Chat":
            msg_box.chat_title = title
            
        pane_id = f"tab-{new_chat_id}"
        new_pane = TabPane(title, msg_box, id=pane_id)
        await tabs.add_pane(new_pane)
        tabs.active = pane_id

    async def close_current_tab(self):
        import inspect
        tabs = self.query_one("#chat_tabs", TabbedContent)
        active_pane_id = tabs.active
        if not active_pane_id:
            return
            
        result = tabs.remove_pane(active_pane_id)
        if inspect.isawaitable(result):
            await result
        
        # If no tabs remain, active will be empty or None
        # Also check if it's the last pane being removed
        if not tabs.active or len(list(tabs.query(TabPane))) == 0:
            await self.add_chat_tab()
