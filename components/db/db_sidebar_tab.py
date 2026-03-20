import csv
import os
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal, VerticalScroll
from textual.widgets import Button, Label, Input, DataTable
from textual import on

from components.utils.input_modal import InputModal
from components.utils.form_modal import FormModal
from components.db.results_modal import ResultsModal
from components.db.db_tree import DBTree
from utils.cfg_man import cfg
from utils.db import db_manager
from utils.icons import EXPORT_CSV, OPEN_EXTERNAL, RUN


class DBSidebarTab(Vertical):


  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self.selected_db_path = None
    self.last_columns = []
    self.last_rows = []

  def _on_db_select(self, path: str) -> None:
    self.selected_db_path = path
    label = self.query_one("#db_selected_label", Label)
    label.update(f"Selected: {os.path.basename(path)}")

  def compose(self) -> ComposeResult:
    from components.utils.buttons import ActionButton, RunButton, AddButton
    with VerticalScroll(id="db_tree_container"):
      yield AddButton(action=self.on_add_connection, label="Add Connection", id="btn_add_db_conn", variant="primary")
      yield DBTree(id="db_tree", on_select=self._on_db_select)

    with Vertical(id="db_query_pane"):
      yield Label("No database selected", id="db_selected_label")
      with Horizontal(id="db_query_input_container"):
        yield Input(placeholder="Enter SQL query...", id="db_query_input")
        yield ActionButton(OPEN_EXTERNAL, action=self.on_popout_query, id="btn_popout_query", tooltip="Open Query Editor", classes="action-btn icon-btn")
        yield RunButton(action=self.on_run_query, id="btn_run_query", tooltip="Run Query", classes="action-btn icon-btn")
      with Horizontal(id="db_results_header"):
        yield Label("Results:")
        yield ActionButton(OPEN_EXTERNAL, action=self.on_popout_results, id="btn_popout_results", tooltip="Open Results Pane", classes="action-btn icon-btn")
        yield ActionButton(EXPORT_CSV, action=self.on_export_csv, id="btn_export_csv", tooltip="Export to CSV", classes="action-btn icon-btn")
      yield DataTable(id="db_query_results")

  def on_mount(self) -> None:
    pass

  def _refresh_tree(self) -> None:
    tree = self.query_one("#db_tree", DBTree)
    tree.reload()

  def on_add_connection(self) -> None:
    schema = [
      {"key": "label", "label": "Label", "type": "text", "placeholder": "e.g. Production DB"},
      {"key": "path", "label": "Path / URL", "type": "text", "required": True},
      {"key": "type", "label": "Type", "type": "text", "placeholder": "e.g. sqlite3"},
    ]

    def on_save(result: dict | None) -> None:
      if result and result.get("path"):
        db_manager.add_connection(result["path"], label=result.get("label"), conn_type=result.get("type"))
        self._refresh_tree()

    self.app.push_screen(FormModal("Add Connection", schema=schema, callback=on_save))

  def on_popout_query(self) -> None:
    query_input = self.query_one("#db_query_input", Input)

    def check_modal_result(result: str | None) -> None:
      if result is not None:
        query_input.value = result

    self.app.push_screen(
      InputModal("SQL Query Editor", initial_value=query_input.value, multiline=True, language="sql", code_editor=True),
      check_modal_result,
    )

  def _export_to_csv(self, filename: str) -> None:
    if not filename.strip():
      return
    if not filename.endswith(".csv"):
      filename = f"{filename}.csv"
    working_dir = cfg.get("session.working_directory", ".")
    path = os.path.join(working_dir, filename)
    try:
      with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if self.last_columns:
          writer.writerow(self.last_columns)
        writer.writerows(self.last_rows)
      self.app.notify(f"Exported to {path}", severity="information")
    except Exception as e:
      self.app.notify(f"Export failed: {e}", severity="error")

  def on_export_csv(self) -> None:
    if not self.last_columns and not self.last_rows:
      self.app.notify("No results to export.", severity="warning")
      return

    def check_modal_result(result: str | None) -> None:
      if result:
        self._export_to_csv(result)

    self.app.push_screen(InputModal("Export filename"), check_modal_result)

  def on_popout_results(self) -> None:
    working_dir = cfg.get("session.working_directory", ".")
    self.app.push_screen(ResultsModal("Query Results", self.last_columns, self.last_rows, working_dir))

  @on(Input.Submitted, "#db_query_input")
  async def on_run_query(self) -> None:
    if not self.selected_db_path:
      self.app.notify("Please select a database from the tree first.", severity="warning")
      return

    query_input = self.query_one("#db_query_input", Input)
    query = query_input.value.strip()

    if not query:
      return

    table = self.query_one("#db_query_results", DataTable)
    table.clear(columns=True)

    self.last_columns = []
    self.last_rows = []

    try:
      cols, results = await db_manager.execute(self.selected_db_path, query)

      if cols:
        self.last_columns = cols
        table.add_columns(*cols)

      if results:
        for row in results:
          str_row = [str(item) if item is not None else "NULL" for item in row]
          self.last_rows.append(str_row)
          table.add_row(*str_row)
      else:
        if not cols:
          self.last_columns = ["Result"]
          table.add_columns("Result")

        msg = "Query executed successfully (no rows returned)."
        self.last_rows = [[msg]]
        table.add_row(msg)

    except Exception as e:
      self.last_columns = ["Error"]
      self.last_rows = [[str(e)]]
      table.add_columns("Error")
      table.add_row(str(e))
