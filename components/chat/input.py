from textual import on
from textual.widgets import TextArea, OptionList
from textual.widgets.option_list import Option
import os
from utils.db import db_manager
from utils.cmd_loader import load_commands


def _offset_to_location(text: str, offset: int) -> tuple[int, int]:
  """Convert character offset to (row, col) for TextArea."""
  lines = text.split('\n')
  for row, line in enumerate(lines):
    if offset <= len(line):
      return (row, offset)
    offset -= len(line) + 1
  return (len(lines) - 1, len(lines[-1]) if lines else 0)


def _location_to_offset(text: str, row: int, col: int) -> int:
  """Convert (row, col) to character offset."""
  lines = text.split('\n')
  return sum(len(l) + 1 for l in lines[:row]) + col


class MessageInput(TextArea):
  def __init__(self, actor, id, **kwargs):
    self.box_id = id
    self.actor = actor
    self.input_history = []
    self.history_index = -1
    self.current_input = ""
    self.commands = {}
    self.files = []
    self._just_autocompleted = False
    super().__init__(id=f'input_{id}', **kwargs)

  @property
  def value(self) -> str:
    return self.text

  @value.setter
  def value(self, val: str) -> None:
    self.text = val

  def _cursor_to_end(self) -> None:
    lines = self.text.split('\n')
    self.cursor_location = (len(lines) - 1, len(lines[-1]) if lines else 0)

  def on_mount(self):
    self.app.run_worker(self._load_history())
    self.app.run_worker(self._load_files())
    app_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    self.commands = load_commands()

  async def _load_files(self):
    from utils.cfg_man import cfg
    self.files = []
    root_dir = cfg.get('session.working_directory')
    for root, dirs, files in os.walk(root_dir):
      dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('__pycache__', 'node_modules', '.venv')]
      for file in files:
        if not file.startswith('.'):
          full_path = os.path.join(root, file)
          rel_path = os.path.relpath(full_path, root_dir)
          self.files.append(rel_path)

  async def _load_history(self):
    db_path = db_manager.get_project_db_path()
    query = "SELECT user_input FROM input_history ORDER BY id ASC"
    try:
      cols, results = await db_manager.execute(db_path, query)
      if results:
        self.input_history = [row[0] for row in results]
        self.history_index = len(self.input_history)
    except Exception as e:
      print(f"Failed to load input history: {e}")

  @on(TextArea.Changed)
  def on_input_changed(self, event: TextArea.Changed) -> None:
    try:
      cmdlist = self.screen.query_one(f'#autocomplete_{self.box_id}', OptionList)
    except Exception:
      return
    val = self.text
    row, col = self.cursor_location
    cursor_pos = _location_to_offset(val, row, col)
    text_before_cursor = val[:cursor_pos]
    if text_before_cursor and text_before_cursor[-1].isspace():
      current_word = ""
    else:
      words = text_before_cursor.split()
      current_word = words[-1] if words else ""
    if text_before_cursor.startswith('/') and ' ' not in text_before_cursor:
      cmdlist.styles.display = "block"
      search_term = text_before_cursor[1:].lower()
      cmdlist.clear_options()
      for cmd_name, cmd_obj in self.commands.items():
        if search_term in cmd_name.lower():
          cmdlist.add_option(Option(f"/{cmd_name} - {cmd_obj.description}", id=f"cmd_{cmd_name}"))
      if cmdlist.option_count > 0:
        cmdlist.highlighted = 0
      else:
        cmdlist.styles.display = "none"
    elif current_word.startswith('@'):
      cmdlist.styles.display = "block"
      search_term = current_word[1:].lower()
      cmdlist.clear_options()
      matches = [f for f in self.files if search_term in f.lower()]
      for f in matches[:20]:
        cmdlist.add_option(Option(f"@{f}", id=f"file_{f}"))
      if cmdlist.option_count > 0:
        cmdlist.highlighted = 0
      else:
        cmdlist.styles.display = "none"
    else:
      cmdlist.styles.display = "none"

  async def on_key(self, event) -> None:
    try:
      cmdlist = self.screen.query_one(f'#autocomplete_{self.box_id}', OptionList)
      cmdlist_visible = cmdlist.styles.display == "block"
    except Exception:
      cmdlist = None
      cmdlist_visible = False
    if cmdlist_visible and event.key in ("up", "down", "enter", "tab"):
      if event.key == "up":
        if cmdlist.highlighted is not None and cmdlist.highlighted > 0:
          cmdlist.highlighted -= 1
        event.prevent_default()
        event.stop()
      elif event.key == "down":
        if cmdlist.highlighted is not None and cmdlist.highlighted < cmdlist.option_count - 1:
          cmdlist.highlighted += 1
        event.prevent_default()
        event.stop()
      elif event.key in ("enter", "tab"):
        if cmdlist.highlighted is not None:
          opt = cmdlist.get_option_at_index(cmdlist.highlighted)
          val = self.text
          row, col = self.cursor_location
          cursor_pos = _location_to_offset(val, row, col)
          last_space = val.rfind(' ', 0, cursor_pos)
          start_idx = last_space + 1 if last_space != -1 else 0
          if opt.id.startswith("cmd_"):
            replacement = f"/{opt.id[4:]} "
          elif opt.id.startswith("file_"):
            replacement = f"@{opt.id[5:]} "
          else:
            replacement = ""
          start_loc = _offset_to_location(val, start_idx)
          end_loc = _offset_to_location(val, cursor_pos)
          self.replace(replacement, start_loc, end_loc)
          cmdlist.styles.display = "none"
          if event.key == "enter":
            self._just_autocompleted = True
          self.focus()
        event.prevent_default()
        event.stop()
      return
    if event.key == "up":
      if self.history_index == len(self.input_history):
        self.current_input = self.text
      if self.history_index > 0:
        self.history_index -= 1
        self.text = self.input_history[self.history_index]
        self._cursor_to_end()
        event.prevent_default()
    elif event.key == "down":
      if self.history_index < len(self.input_history) - 1:
        self.history_index += 1
        self.text = self.input_history[self.history_index]
        self._cursor_to_end()
        event.prevent_default()
      elif self.history_index == len(self.input_history) - 1:
        self.history_index = len(self.input_history)
        self.text = self.current_input
        self._cursor_to_end()
        event.prevent_default()
    elif event.key == "shift+enter":
      event.prevent_default()
      self.insert("\n")
      return
    elif event.key == "enter":
      event.prevent_default()
      self._submit()
      return

  def _submit(self) -> None:
    if self._just_autocompleted:
      self._just_autocompleted = False
      return
    if not self.text.strip():
      return
    try:
      cmdlist = self.screen.query_one(f'#autocomplete_{self.box_id}', OptionList)
      if cmdlist.styles.display == "block":
        cmdlist.styles.display = "none"
    except Exception:
      pass
    box = self.screen.query_one(f'#chat_box-{self.box_id}')
    val = self.text.strip()
    if val.startswith('/'):
      parts = val[1:].strip().split()
      if not parts:
        self.text = ""
        return
      cmd_name = parts[0]
      args = parts[1:]
      if cmd_name in self.commands:
        cmd_obj = self.commands[cmd_name]
        self.app.run_worker(cmd_obj.execute(self.app, args))
      self.text = ""
      return
    user_text = val
    if not user_text:
      return
    self.text = ""
    import re
    from utils.cfg_man import cfg
    file_matches = re.findall(r'@(\S+)', user_text)
    agent_text = re.sub(r'\s*@\S+', '', user_text).strip()
    app_dir = cfg.get('session.working_directory')
    appended_files_text = ""
    for f in file_matches:
      file_path = os.path.join(app_dir, f)
      if os.path.isfile(file_path):
        try:
          with open(file_path, 'r', encoding='utf-8') as file_obj:
            content = file_obj.read()
            ext = os.path.splitext(f)[1][1:]
            if not ext:
              ext = "text"
            appended_files_text += f"\n\n`{f}`:\n```{ext}\n{content}\n```"
        except Exception as e:
          appended_files_text += f"\n\nError reading `{f}`: {e}"
    if user_text not in self.input_history:
      db_path = db_manager.get_project_db_path()
      query = "INSERT INTO input_history (user_input) VALUES (?)"
      self.app.run_worker(db_manager.execute(db_path, query, (user_text,)))
      self.input_history.append(user_text)
    self.history_index = len(self.input_history)
    self.current_input = ""
    display_content = user_text + appended_files_text if appended_files_text else user_text
    agent_content = agent_text + appended_files_text if appended_files_text else agent_text
    raw_query = display_content.split("\n\n`")[0].strip() if "\n\n`" in display_content else display_content
    if not any(m.get("role") == "user" for m in box.messages):
      box.chat_title = raw_query[:15] + "..." if len(raw_query) > 15 else raw_query
    from utils.git import create_checkpoint
    checkpoint_msg = f"Cody checkpoint: {agent_text[:50]}..." if len(agent_text) > 50 else f"Cody checkpoint: {agent_text}"
    git_checkpoint = create_checkpoint(app_dir, checkpoint_msg)
    user_msg = {"role": "user", "content": display_content}
    if git_checkpoint:
      user_msg["git_checkpoint"] = git_checkpoint
    msgs = [*box.messages, user_msg]
    placeholder_id = f"pending_{len(msgs)}"
    msgs.append({
      "id": placeholder_id,
      "role": "assistant",
      "content": "Thinking…",
      "loading": True,
    })
    box.messages = msgs
    self.app.run_worker(
      box.get_agent_response(agent_content, placeholder_id, git_checkpoint),
      exclusive=False,
    )
