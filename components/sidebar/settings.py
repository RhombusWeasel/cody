"""Settings sidebar tab - one SettingsTree per top-level config section."""
from textual.app import ComposeResult
from textual.containers import VerticalScroll, Vertical
from textual.widgets import Input, Switch, Label
from textual import on

from components.tree.generic_tree import GenericTree
from components.utils.input_modal import InputModal
from components.utils.form_modal import FormModal
from utils.tree_model import TreeEntry
from utils.cfg_man import cfg
import utils.icons as icons

SECTION_ICONS: dict[str, str] = {
    "session":    icons.SETTINGS,
    "providers":  icons.CHATS,
    "interface":  icons.FILE_SYSTEM,
    "prompts":    icons.EDIT,
    "skills":     icons.SKILLS,
    "db":         icons.DB,
}


def _is_password_field(path: str) -> bool:
    key = path.split('.')[-1].lower()
    return any(x in key for x in ("password", "token", "api_key", "secret"))


def _is_focused_within(widget) -> bool:
    focused = widget.app.focused
    if focused is None:
        return False
    node = focused
    while node is not None:
        if node is widget:
            return True
        node = node.parent
    return False


class SettingsTree(GenericTree):
    """Config editor tree for a single top-level config section."""

    def __init__(self, section_key: str, icon: str, **kwargs):
        super().__init__(**kwargs)
        self._section_key = section_key
        self._section_icon = icon

    # --- tree entry building ---

    def get_visible_entries(self) -> list[TreeEntry]:
        entries = []
        val = cfg.data.get(self._section_key)
        is_exp = self._section_key in self._expanded

        entries.append(TreeEntry(
            node_id=self._section_key,
            indent="",
            is_expandable=True,
            is_expanded=is_exp,
            display_name=self._section_key.replace('_', ' ').title(),
            icon=self._section_icon,
        ))

        if is_exp and val is not None:
            if isinstance(val, dict):
                self._walk(val, self._section_key, [], entries)
            elif isinstance(val, list):
                self._walk_list(val, self._section_key, [], entries)

        return entries

    def _build_indent(self, ancestors_last: list[bool]) -> str:
        return "".join(self.SPACER if last else self.VERTICAL for last in ancestors_last)

    def _walk(self, data: dict, path: str, ancestors_last: list[bool], entries: list) -> None:
        items = list(data.items())
        for i, (key, val) in enumerate(items):
            is_last = i == len(items) - 1
            node_path = f"{path}.{key}"
            indent = self._build_indent(ancestors_last)
            branch = self.LAST_BRANCH if is_last else self.BRANCH
            label = str(key).replace('_', ' ').title()

            if isinstance(val, (dict, list)):
                is_exp = node_path in self._expanded
                entries.append(TreeEntry(
                    node_id=node_path,
                    indent=indent + branch,
                    is_expandable=True,
                    is_expanded=is_exp,
                    display_name=label,
                    icon=icons.FOLDER,
                ))
                if is_exp:
                    if isinstance(val, dict):
                        self._walk(val, node_path, ancestors_last + [is_last], entries)
                    elif node_path == "db.connections":
                        self._walk_conn_list(val, node_path, ancestors_last + [is_last], entries)
                    else:
                        self._walk_list(val, node_path, ancestors_last + [is_last], entries)
            else:
                entries.append(TreeEntry(
                    node_id=node_path,
                    indent=indent + branch,
                    is_expandable=False,
                    is_expanded=False,
                    display_name=str(key).replace('_', ' '),
                    icon=icons.FILE,
                ))

    def _walk_list(self, lst: list, path: str, ancestors_last: list[bool], entries: list) -> None:
        for i, item in enumerate(lst):
            is_last = i == len(lst) - 1
            item_path = f"{path}.{i}"
            indent = self._build_indent(ancestors_last)
            branch = self.LAST_BRANCH if is_last else self.BRANCH

            if isinstance(item, dict):
                is_exp = item_path in self._expanded
                entries.append(TreeEntry(
                    node_id=item_path,
                    indent=indent + branch,
                    is_expandable=True,
                    is_expanded=is_exp,
                    display_name=f"Item {i}",
                    icon=icons.FOLDER,
                ))
                if is_exp:
                    self._walk(item, item_path, ancestors_last + [is_last], entries)
            else:
                entries.append(TreeEntry(
                    node_id=item_path,
                    indent=indent + branch,
                    is_expandable=False,
                    is_expanded=False,
                    display_name="",
                    icon=icons.FILE,
                ))

    def _walk_conn_list(self, lst: list, path: str, ancestors_last: list[bool], entries: list) -> None:
        for i, item in enumerate(lst):
            is_last = i == len(lst) - 1
            item_path = f"{path}.{i}"
            indent = self._build_indent(ancestors_last)
            branch = self.LAST_BRANCH if is_last else self.BRANCH
            label = (
                item.get("label") or item.get("path", f"Connection {i}")
            ) if isinstance(item, dict) else str(item)
            entries.append(TreeEntry(
                node_id=item_path,
                indent=indent + branch,
                is_expandable=False,
                is_expanded=False,
                display_name=label,
                icon=icons.DB,
            ))

    # --- editor widgets per node ---

    def _is_conn_item(self, node_id: str) -> bool:
        parts = node_id.split('.')
        return parts[-1].isdigit() and '.'.join(parts[:-1]) == "db.connections"

    def get_node_buttons(self, node_id: str, is_expandable: bool) -> list:
        from components.utils.buttons import EditButton, DeleteButton, AddButton
        if node_id == self._section_key:
            return []

        if self._is_conn_item(node_id):
            return [
                EditButton(action=lambda n=node_id: self.on_button_action(n, "edit_conn"), tooltip="Edit connection", classes="action-btn settings-edit-btn"),
                DeleteButton(action=lambda n=node_id: self.on_button_action(n, "delete"), tooltip="Delete connection", classes="action-btn settings-del-btn"),
            ]

        val = cfg.get(node_id)
        parts = node_id.split('.')
        is_list_item = parts[-1].isdigit()

        if isinstance(val, dict):
            if is_list_item:
                return [DeleteButton(action=lambda n=node_id: self.on_button_action(n, "delete"), tooltip="Delete item", classes="action-btn settings-del-btn")]
            return []

        if isinstance(val, list):
            return [AddButton(action=lambda n=node_id: self.on_button_action(n, "add"), tooltip="Add item", classes="action-btn settings-add-btn")]

        if is_list_item:
            return [
                Input(
                    value=str(val) if val is not None else "",
                    password=_is_password_field(node_id),
                    classes="settings-input",
                ),
                DeleteButton(action=lambda n=node_id: self.on_button_action(n, "delete"), tooltip="Delete", classes="action-btn settings-del-btn"),
            ]

        if isinstance(val, bool):
            return [Switch(value=val, classes="settings-switch")]

        if isinstance(val, str) and '\n' in val:
            return [EditButton(action=lambda n=node_id: self.on_button_action(n, "edit"), tooltip="Edit", classes="action-btn settings-edit-btn")]

        return [Input(
            value=str(val) if val is not None else "",
            password=_is_password_field(node_id),
            classes="settings-input",
        )]

    # --- actions ---

    def on_button_action(self, node_id: str, action: str) -> None:
        if action == "edit_conn":
            val = cfg.get(node_id)
            if not isinstance(val, dict):
                return
            schema = [
                {"key": "label", "label": "Label", "type": "text", "placeholder": "e.g. Production DB"},
                {"key": "path", "label": "Path / URL", "type": "text", "required": True},
                {"key": "type", "label": "Type", "type": "text", "placeholder": "e.g. sqlite3"},
            ]

            def _save(result: dict | None) -> None:
                if result:
                    cfg.set(node_id, result)
                    cfg.changed = False
                    self.reload()

            self.app.push_screen(FormModal("Edit Connection", schema=schema, args=val, callback=_save))

        elif action == "add":
            lst = cfg.get(node_id)
            if not isinstance(lst, list):
                return
            new_item = {k: "" for k in lst[0].keys()} if lst and isinstance(lst[0], dict) else ""
            lst.append(new_item)
            cfg.set(node_id, lst)
            cfg.changed = False
            self._expanded.add(node_id)
            self.reload()

        elif action == "delete":
            parts = node_id.split('.')
            if not parts[-1].isdigit():
                return
            idx = int(parts[-1])
            list_path = '.'.join(parts[:-1])
            lst = cfg.get(list_path)
            if isinstance(lst, list) and idx < len(lst):
                lst.pop(idx)
                cfg.set(list_path, lst)
                cfg.changed = False
                self.reload()

        elif action == "edit":
            val = cfg.get(node_id)
            title = node_id.split('.')[-1].replace('_', ' ').title()

            def _save(new_val: str | None) -> None:
                if new_val is not None:
                    cfg.set(node_id, new_val)
                    cfg.changed = False

            self.app.push_screen(
                InputModal(title, initial_value=str(val or ""), multiline=True),
                _save,
            )

    @on(Input.Changed)
    def _on_input_changed(self, event: Input.Changed) -> None:
        path = getattr(event.input, 'node_id', None)
        if path is None:
            return
        val: str | int | float = event.value
        original = cfg.get(path)
        if isinstance(original, int):
            try:
                val = int(val)
            except ValueError:
                pass
        elif isinstance(original, float):
            try:
                val = float(val)
            except ValueError:
                pass
        cfg.set(path, val)
        cfg.changed = False

    @on(Switch.Changed)
    def _on_switch_changed(self, event: Switch.Changed) -> None:
        path = getattr(event.switch, 'node_id', None)
        if path is None:
            return
        cfg.set(path, event.value)
        cfg.changed = False


class SettingsMenu(Vertical):

    def on_mount(self) -> None:
        self.set_interval(1.0, self._check_config)

    def _check_config(self) -> None:
        if not cfg.changed or _is_focused_within(self):
            return
        cfg.changed = False
        for tree in self.query(SettingsTree):
            tree.reload()

    def compose(self) -> ComposeResult:
        yield Label("Settings", id="settings-title")
        with VerticalScroll():
            for key in cfg.data:
                yield SettingsTree(
                    section_key=key,
                    icon=SECTION_ICONS.get(key, icons.FOLDER),
                )
