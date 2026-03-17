from textual.widgets import Static

sidebar_label = "File Tools"

class SidebarWidget(Static):
  def compose(self):
    yield Static("File manipulation tools")
