"""Agents sidebar tab — CRUD for user-defined sub-agents stored in the DB."""
import json
import uuid
from typing import Any

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widget import Widget
from textual.widgets import Label, TextArea
from textual import work

from components.tree.generic_tree import GenericTree
from components.tree.tree_row import TreeRow
from components.utils.form_modal import FormModal
from components.utils.input_modal import InputModal
from utils.db import db_manager
from utils.tree_model import TreeEntry
import utils.icons as icons
from utils.icons import DELETE, EDIT

sidebar_label = "󱙺"
_ROOT_ID = "__agents_root__"
sidebar_tooltip = "Agents"

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

_EMPTY_NODE = "__empty__"
_DESC_TAG = "desc"


def _agent_label_rich(agent: dict) -> Text:
  name = agent.get("name", "")
  prov = agent.get("provider") or ""
  model = agent.get("model") or ""
  prov_col = f"{prov}/{model}" if prov or model else "(active)"
  t = Text(name)
  t.append("  ")
  t.append(prov_col, style="dim")
  return t


class AgentDescriptionRow(Widget):
  """Read-only description under an expanded agent (aligned with tree columns)."""

  def __init__(self, indent: str, text: str, **kwargs):
    super().__init__(**kwargs)
    self._indent = indent
    self._text = text or ""

  def compose(self) -> ComposeResult:
    with Horizontal(classes="agent-desc-row"):
      yield Label(self._indent, classes="tree-indent", markup=False)
      yield Label("  ", classes="tree-expand", markup=False)
      yield TextArea(
        self._text,
        read_only=True,
        classes="agent-desc-textarea",
      )


class AgentsTree(GenericTree):
  """Agents under an expandable root row; add on root, edit/delete on each agent."""

  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self._agents: list[dict] = []
    self._expanded.add(_ROOT_ID)

  def on_mount(self) -> None:
    super().on_mount()
    self.load_agents()

  @work
  async def load_agents(self) -> None:
    self._agents = await db_manager.get_agents()
    self.reload()

  def get_visible_entries(self) -> list[TreeEntry]:
    entries: list[TreeEntry] = []
    root_open = _ROOT_ID in self._expanded
    entries.append(TreeEntry(
      node_id=_ROOT_ID,
      indent="",
      is_expandable=True,
      is_expanded=root_open,
      display_name="Agents",
      icon=icons.FOLDER,
    ))
    if not root_open:
      return entries
    if not self._agents:
      entries.append(TreeEntry(
        node_id=_EMPTY_NODE,
        indent=self.LAST_BRANCH,
        is_expandable=False,
        is_expanded=False,
        display_name="(no agents)",
        icon=" ",
      ))
      return entries
    for i, agent in enumerate(self._agents):
      is_last = i == len(self._agents) - 1
      branch = self.LAST_BRANCH if is_last else self.BRANCH
      aid = agent["id"]
      is_exp = aid in self._expanded
      entries.append(TreeEntry(
        node_id=aid,
        indent=branch,
        is_expandable=True,
        is_expanded=is_exp,
        display_name=agent.get("name", ""),
        icon=sidebar_label,
        display_rich=_agent_label_rich(agent),
      ))
      if is_exp:
        ext = self.SPACER if is_last else self.VERTICAL
        entries.append(TreeEntry(
          node_id=(_DESC_TAG, aid),
          indent=ext + self.LAST_BRANCH,
          is_expandable=False,
          is_expanded=False,
          display_name="",
          icon=" ",
        ))
    return entries

  def create_row_widget(self, entry: TreeEntry) -> Widget:
    nid = entry.node_id
    if isinstance(nid, tuple) and len(nid) == 2 and nid[0] == _DESC_TAG:
      aid = nid[1]
      agent = next((a for a in self._agents if a["id"] == aid), None)
      body = (agent.get("description") or "") if agent else ""
      return AgentDescriptionRow(indent=entry.indent, text=body)
    return TreeRow(
      node_id=entry.node_id,
      indent=entry.indent,
      is_expandable=entry.is_expandable,
      is_expanded=entry.is_expanded,
      display_name=entry.display_name,
      icon=entry.icon,
      display_rich=entry.display_rich,
      button_factory=lambda nid, exp: self._get_buttons_for_entry(nid, exp),
    )

  def get_node_buttons(self, node_id: Any, is_expandable: bool) -> list:
    from components.utils.buttons import AddButton, EditButton, DeleteButton
    if node_id == _ROOT_ID:
      return [
        AddButton(
          action=lambda: self.on_button_action(_ROOT_ID, "add"),
          tooltip="Add agent",
          label=icons.NEW_FILE,
          classes="action-btn agent-btn",
        ),
      ]
    if node_id == _EMPTY_NODE:
      return []
    if isinstance(node_id, tuple) and node_id[0] == _DESC_TAG:
      return []
    return [
      EditButton(
        action=lambda n=node_id: self.on_button_action(n, "edit"),
        label=EDIT,
        tooltip="Edit agent",
        classes="action-btn agent-btn",
      ),
      DeleteButton(
        action=lambda n=node_id: self.on_button_action(n, "delete"),
        label=DELETE,
        tooltip="Delete agent",
        classes="action-btn agent-btn agent-btn-danger",
      ),
    ]

  def on_button_action(self, node_id: Any, action: str) -> None:
    if action == "add":
      self.open_add()
    elif action == "edit":
      self._edit_agent(str(node_id))
    elif action == "delete":
      self._confirm_delete(str(node_id))

  @work
  async def _edit_agent(self, agent_id: str) -> None:
    agent = await db_manager.get_agent_by_name_or_id(agent_id)
    if agent:
      self._open_form(agent)

  def _confirm_delete(self, agent_id: str) -> None:
    def on_confirm(result) -> None:
      if result is not None:
        self._delete_agent(agent_id)

    self.app.push_screen(
      InputModal("Delete this agent? This cannot be undone.", confirm_only=True),
      on_confirm,
    )

  @work
  async def _delete_agent(self, agent_id: str) -> None:
    await db_manager.delete_agent(agent_id)
    self.app.notify("Agent deleted.")
    self.load_agents()

  def open_add(self) -> None:
    self._open_form(None)

  def _open_form(self, existing: dict | None = None) -> None:
    groups_str = ""
    agent_id = str(uuid.uuid4())
    args = {"id": agent_id}

    if existing:
      agent_id = existing["id"]
      groups_str = ", ".join(json.loads(existing["tool_groups"])) if existing.get("tool_groups") else ""
      args = {
        "id": existing["id"],
        "name": existing.get("name", ""),
        "description": existing.get("description", ""),
        "provider": existing.get("provider", "") or "",
        "model": existing.get("model", "") or "",
        "tool_groups": groups_str,
        "system_prompt": existing.get("system_prompt", "") or "",
      }

    title = "Edit Agent" if existing else "Add Agent"
    self.app.push_screen(
      FormModal(title=title, schema=AGENT_SCHEMA, args=args, callback=self._on_form_result),
    )

  def _on_form_result(self, data: dict) -> None:
    self._save_agent(data)

  @work
  async def _save_agent(self, data: dict) -> None:
    groups = json.dumps([g.strip() for g in data.get("tool_groups", "").split(",") if g.strip()])
    await db_manager.save_agent(
      data["id"],
      data["name"],
      data.get("description", ""),
      data.get("system_prompt", ""),
      groups,
      data.get("provider") or None,
      data.get("model") or None,
    )
    self.app.notify(f"Agent '{data['name']}' saved.")
    self.load_agents()


class AgentsSidebarTab(Vertical):

  def compose(self) -> ComposeResult:
    yield Label(f"{sidebar_label} Agents", id="agents_tab_title")
    with VerticalScroll(id="agents_tree_scroll"):
      yield AgentsTree(id="agents_tree")


def get_sidebar_widget():
  return AgentsSidebarTab()
