"""Agents sidebar tab — CRUD for user-defined sub-agents stored in the DB."""
import asyncio
import json
import uuid

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Button, Label, DataTable
from textual import on

from components.utils.form_modal import FormModal
from components.utils.input_modal import InputModal
from utils.db import db_manager
from utils.icons import AGENTS
import utils.icons as icons

AGENT_SCHEMA = [
  {"key": "name",        "label": "Name",        "type": "text",     "placeholder": "e.g. code-reviewer", "required": True},
  {"key": "description", "label": "Description", "type": "text",     "placeholder": "What this agent does"},
  {"type": "row", "fields": [
    {"key": "provider", "label": "Provider", "type": "text", "placeholder": "blank = active"},
    {"key": "model",    "label": "Model",    "type": "text", "placeholder": "blank = default"},
  ]},
  {"key": "tool_groups",   "label": "Tool Groups (comma-separated)", "type": "text",     "placeholder": "e.g. system, git"},
  {"key": "system_prompt", "label": "System Prompt",                 "type": "textarea"},
]

sidebar_label = AGENTS
sidebar_tooltip = "Agents"


class AgentsSidebarTab(Vertical):

  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self._row_key_to_id: dict[str, str] = {}
    self._selected_agent_id: str | None = None

  def compose(self) -> ComposeResult:
    from components.utils.buttons import EditButton, DeleteButton, AddButton
    yield Label(f"{icons.AGENTS} Agents", id="agents_tab_title")
    yield DataTable(id="agents_table", show_cursor=True, zebra_stripes=True)
    with Horizontal(id="agents_actions"):
      yield EditButton(action=self._on_edit, id="btn_edit_agent", label=f"{icons.EDIT} Edit", classes="action-btn agent-btn", disabled=True)
      yield DeleteButton(action=self._on_delete, id="btn_delete_agent", label=f"{icons.DELETE} Delete", classes="action-btn agent-btn agent-btn-danger", disabled=True)
    yield AddButton(action=self._on_add, id="btn_add_agent", label=f"+ Add Agent", variant="primary")

  def on_mount(self) -> None:
    table = self.query_one("#agents_table", DataTable)
    table.add_columns("Name", "Description", "Provider")
    self.call_after_refresh(self._load_agents)

  def _load_agents(self) -> None:
    asyncio.get_event_loop().create_task(self._refresh())

  async def _refresh(self) -> None:
    agents = await db_manager.get_agents()
    table = self.query_one("#agents_table", DataTable)
    table.clear()
    self._row_key_to_id = {}
    self._selected_agent_id = None
    self._set_action_buttons(False)

    for agent in agents:
      provider = agent.get('provider') or ''
      model = agent.get('model') or ''
      provider_col = f"{provider}/{model}" if provider or model else '(active)'
      table.add_row(
        agent['name'],
        agent.get('description') or '',
        provider_col,
        key=agent['id'],
      )
      self._row_key_to_id[agent['id']] = agent['id']

  def _set_action_buttons(self, enabled: bool) -> None:
    self.query_one("#btn_edit_agent", Button).disabled = not enabled
    self.query_one("#btn_delete_agent", Button).disabled = not enabled

  @on(DataTable.RowSelected, "#agents_table")
  def _on_row_selected(self, event: DataTable.RowSelected) -> None:
    self._selected_agent_id = str(event.row_key.value) if event.row_key else None
    self._set_action_buttons(self._selected_agent_id is not None)

  def _open_form(self, existing: dict | None = None) -> None:
    groups_str = ''
    agent_id = str(uuid.uuid4())
    args = {"id": agent_id}

    if existing:
      agent_id = existing['id']
      groups_str = ', '.join(json.loads(existing['tool_groups'])) if existing.get('tool_groups') else ''
      args = {
        "id": existing['id'],
        "name": existing.get('name', ''),
        "description": existing.get('description', ''),
        "provider": existing.get('provider', '') or '',
        "model": existing.get('model', '') or '',
        "tool_groups": groups_str,
        "system_prompt": existing.get('system_prompt', '') or '',
      }

    title = "Edit Agent" if existing else "Add Agent"
    self.app.push_screen(FormModal(title=title, schema=AGENT_SCHEMA, args=args, callback=self._on_form_result))

  # --- Add ---

  def _on_add(self) -> None:
    self._open_form()

  # --- Edit ---

  def _on_edit(self) -> None:
    if not self._selected_agent_id:
      return
    asyncio.get_event_loop().create_task(self._load_and_edit(self._selected_agent_id))

  async def _load_and_edit(self, agent_id: str) -> None:
    agent = await db_manager.get_agent_by_name_or_id(agent_id)
    if agent:
      self._open_form(agent)

  # --- Delete ---

  def _on_delete(self) -> None:
    if not self._selected_agent_id:
      return
    agent_id = self._selected_agent_id

    def on_confirm(result) -> None:
      if result is not None:
        asyncio.get_event_loop().create_task(self._do_delete(agent_id))

    self.app.push_screen(
      InputModal("Delete this agent? This cannot be undone.", confirm_only=True),
      on_confirm,
    )

  async def _do_delete(self, agent_id: str) -> None:
    await db_manager.delete_agent(agent_id)
    self.app.notify("Agent deleted.")
    await self._refresh()

  # --- Form result ---

  def _on_form_result(self, data: dict) -> None:
    asyncio.get_event_loop().create_task(self._save_agent(data))

  async def _save_agent(self, data: dict) -> None:
    groups = json.dumps([g.strip() for g in data.get('tool_groups', '').split(',') if g.strip()])
    await db_manager.save_agent(
      data['id'],
      data['name'],
      data.get('description', ''),
      data.get('system_prompt', ''),
      groups,
      data.get('provider') or None,
      data.get('model') or None,
    )
    self.app.notify(f"Agent '{data['name']}' saved.")
    await self._refresh()


def get_sidebar_widget():
  return AgentsSidebarTab()
