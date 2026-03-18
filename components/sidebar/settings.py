from textual.app import ComposeResult
from textual.containers import VerticalScroll, Vertical, Horizontal
from textual.widgets import Label, Collapsible, Input, Switch, TextArea, Button
from textual import on

from utils.cfg_man import cfg
from utils.icons import DELETE


class SettingsMenu(VerticalScroll):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.collapsed_state = {}

    def compose(self) -> ComposeResult:
        yield from self.build_settings(cfg.data)

    async def refresh_settings(self):
        await self.remove_children()
        await self.mount(*self.build_settings(cfg.data))

    def build_settings(self, data: dict, path: str = "") -> list:
        widgets = []
        for key, val in data.items():
            current_path = f"{path}.{key}" if path else key
            
            if isinstance(val, dict):
                is_collapsed = self.collapsed_state.get(current_path, False)
                widgets.append(Collapsible(*self.build_settings(val, current_path), title=key.title(), collapsed=is_collapsed, id=f"col_{current_path.replace('.', '__')}"))
            elif isinstance(val, bool):
                widgets.append(Horizontal(
                    Label(key, classes="setting-item-label"), 
                    Switch(value=val, id=f"setting_{current_path.replace('.', '__')}", classes="setting-item-switch"),
                    classes="setting-item"
                ))
            elif isinstance(val, list):
                list_widgets = []
                for i, item in enumerate(val):
                    item_path = f"{current_path}.{i}"
                    if isinstance(item, dict):
                        item_widgets = self.build_settings(item, item_path)
                        item_widgets.append(Button("Delete Item", id=f"del_list_item_{item_path.replace('.', '__')}", variant="error"))
                        is_collapsed = self.collapsed_state.get(item_path, True)
                        list_widgets.append(Collapsible(*item_widgets, title=f"Item {i}", collapsed=is_collapsed, id=f"col_{item_path.replace('.', '__')}"))
                    else:
                        list_widgets.append(Horizontal(
                            Input(value=str(item), id=f"setting_{item_path.replace('.', '__')}", classes="setting-list-input"),
                            Button(DELETE, variant="error", id=f"del_list_item_{item_path.replace('.', '__')}", classes="setting-list-del-btn"),
                            classes="setting-list-row"
                        ))
                list_widgets.append(Button("Add Item", id=f"add_list_item_{current_path.replace('.', '__')}", variant="primary", classes="setting-list-add-btn"))
                is_collapsed = self.collapsed_state.get(current_path, False)
                widgets.append(Collapsible(*list_widgets, title=key.title(), collapsed=is_collapsed, id=f"col_{current_path.replace('.', '__')}"))
            elif isinstance(val, str) and "\n" in val:
                widgets.append(Vertical(
                    Label(key, classes="setting-item-label"),
                    TextArea(text=val, id=f"setting_{current_path.replace('.', '__')}", classes="setting-item-text-area"),
                    classes="setting-item"
                ))
            else:
                is_password = "password" in key.lower() or "token" in key.lower() or "api_key" in key.lower()
                widgets.append(Horizontal(
                    Label(key, classes="setting-item-label"),
                    Input(value=str(val), password=is_password, id=f"setting_{current_path.replace('.', '__')}", classes="setting-item-input"),
                    classes="setting-item"
                ))
        return widgets

    @on(TextArea.Changed)
    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        text_id = event.text_area.id
        if text_id and text_id.startswith("setting_"):
            path = text_id.replace("setting_", "", 1).replace("__", ".")
            cfg.set(path, event.text_area.text)

    @on(Button.Pressed)
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if not btn_id:
            return
            
        if btn_id.startswith("del_list_item_"):
            path = btn_id.replace("del_list_item_", "").replace("__", ".")
            parts = path.split('.')
            if not parts[-1].isdigit():
                return
            index = int(parts[-1])
            list_path = '.'.join(parts[:-1])
            
            lst = cfg.get(list_path)
            if isinstance(lst, list) and index < len(lst):
                lst.pop(index)
                cfg.set(list_path, lst)
                await self.refresh_settings()
                
        elif btn_id.startswith("add_list_item_"):
            path = btn_id.replace("add_list_item_", "").replace("__", ".")
            lst = cfg.get(path)
            if isinstance(lst, list):
                if len(lst) > 0 and isinstance(lst[0], dict):
                    new_item = {k: "" for k in lst[0].keys()}
                    lst.append(new_item)
                else:
                    lst.append("")
                cfg.set(path, lst)
                await self.refresh_settings()

    @on(Input.Changed)
    def on_input_changed(self, event: Input.Changed) -> None:
        input_id = event.input.id
        if input_id and input_id.startswith("setting_"):
            path = input_id.replace("setting_", "", 1).replace("__", ".")
            # Try to infer original type (int, float, etc) or keep as str
            val = event.value
            try:
                # Basic type guessing for numbers if the original was a number
                original_val = cfg.get(path)
                if isinstance(original_val, int):
                    val = int(val)
                elif isinstance(original_val, float):
                    val = float(val)
            except ValueError:
                pass
                
            cfg.set(path, val)

    @on(Switch.Changed)
    def on_switch_changed(self, event: Switch.Changed) -> None:
        switch_id = event.switch.id
        if switch_id and switch_id.startswith("setting_"):
            path = switch_id.replace("setting_", "", 1).replace("__", ".")
            cfg.set(path, event.value)

    @on(Collapsible.Toggled)
    def on_collapsible_toggled(self, event: Collapsible.Toggled) -> None:
        col_id = event.collapsible.id
        if col_id and col_id.startswith("col_"):
            path = col_id.replace("col_", "", 1).replace("__", ".")
            self.collapsed_state[path] = event.collapsible.collapsed
