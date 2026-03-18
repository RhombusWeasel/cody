from textual.widgets import Static

sidebar_label = "File Tools"
sidebar_tooltip = "Example tooltip"

class SidebarWidget(Static):
  def compose(self):
    yield Static("File manipulation tools")
