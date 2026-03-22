from textual import on
from textual.containers import VerticalScroll
from textual.widgets import TabbedContent, TabPane

from components.sidebar.tool_list import ToolList
from components.sidebar.settings import SettingsMenu
from components.db.db_sidebar_tab import DBSidebarTab
from components.fs.file_tree import FileTreeTab
from components.git.git_sidebar_tab import GitSidebarTab
from components.sidebar.chat_history import ChatHistoryTab
from components.sidebar.password_vault_tab import PasswordVaultTab

from utils.cfg_man import cfg
from utils.skill_components import discover_sidebar_tabs
import utils.icons as icons


TAB_TOOLTIPS = {
  "tab-chats": "Chat History",
  "tab-fs": "File System",
  "tab-git": "Git",
  "tab-tools": "Skills",
  "tab-db": "DB Connections",
  "tab-vault": "Password vault",
  "tab-settings": "Settings",
}

class Sidebar(VerticalScroll):
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.visible = cfg.get('interface.sidebar_open_on_start')
        self.set_class(self.visible, '-visible')

    def compose(self):
        with TabbedContent(classes="sidebar-tabbed-content"):
            with TabPane(icons.CHATS, id="tab-chats", classes="tabbed-content-label"):
                yield ChatHistoryTab()
            with TabPane(icons.FILE_SYSTEM, id="tab-fs", classes="tabbed-content-label"):
                yield FileTreeTab()
            with TabPane(icons.GIT, id="tab-git", classes="tabbed-content-label"):
                yield GitSidebarTab()
            with TabPane(icons.SKILLS, id="tab-tools", classes="tabbed-content-label"):
                yield ToolList()
            with TabPane(icons.DB, id="tab-db", classes="tabbed-content-label"):
                yield DBSidebarTab()
            with TabPane(icons.VAULT, id="tab-vault", classes="tabbed-content-label"):
                yield PasswordVaultTab()
            for tab_id, label, factory, tooltip in discover_sidebar_tabs():
                with TabPane(label, id=tab_id, classes="tabbed-content-label"):
                    yield factory()
            with TabPane(icons.SETTINGS, id="tab-settings", classes="tabbed-content-label"):
                yield SettingsMenu()

    def on_mount(self):
        tooltips = dict(TAB_TOOLTIPS)
        for tab_id, _, _, tooltip in discover_sidebar_tabs():
            tooltips[tab_id] = tooltip
        tabs = self.query_one(TabbedContent)
        for pane in tabs.query(TabPane):
            tab_id = pane.id
            if tab_id and (tip := tooltips.get(tab_id)):
                try:
                    tabs.get_tab(tab_id).tooltip = tip
                except ValueError:
                    pass

    @on(TabbedContent.TabActivated)
    def _on_sidebar_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        pane = event.pane
        if pane is None or pane.id != "tab-vault":
            return
        try:
            vault_tab = pane.query_one(PasswordVaultTab)
        except Exception:
            return
        vault_tab.request_unlock_if_needed()