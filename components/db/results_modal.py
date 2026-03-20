import csv
import os
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Label, Button, DataTable
from textual.screen import ModalScreen
from textual import on

from components.utils.input_modal import InputModal
from utils.icons import EXPORT_CSV

class ResultsModal(ModalScreen):


  def __init__(self, title: str, columns: list, rows: list, working_directory: str = "."):
    super().__init__()
    self.title_text = title
    self.columns = columns
    self.rows = rows
    self.working_directory = working_directory

  def compose(self) -> ComposeResult:
    from components.utils.buttons import ActionButton
    with Vertical(id="results_modal_container"):
      with Horizontal(id="results_modal_header"):
        yield Label(self.title_text)
        yield ActionButton(EXPORT_CSV, action=self.on_export_csv, id="btn_results_export_csv", tooltip="Export to CSV", classes="action-btn icon-btn")
      yield DataTable(id="results_modal_table")
      with Horizontal(classes="modal-button-container"):
        yield ActionButton("Close", action=self.on_close, id="btn_results_modal_close", variant="primary", classes="action-btn modal-button")

  def on_mount(self) -> None:
    table = self.query_one("#results_modal_table", DataTable)
    if self.columns:
      table.add_columns(*self.columns)
    if self.rows:
      table.add_rows(self.rows)

  def _export_to_csv(self, filename: str) -> None:
    if not filename.strip():
      return
    if not filename.endswith(".csv"):
      filename = f"{filename}.csv"
    path = os.path.join(self.working_directory, filename)
    try:
      with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if self.columns:
          writer.writerow(self.columns)
        writer.writerows(self.rows)
      self.app.notify(f"Exported to {path}", severity="information")
    except Exception as e:
      self.app.notify(f"Export failed: {e}", severity="error")

  def on_export_csv(self) -> None:
    if not self.columns and not self.rows:
      self.app.notify("No results to export.", severity="warning")
      return

    def check_modal_result(result: str | None) -> None:
      if result:
        self._export_to_csv(result)

    self.app.push_screen(InputModal("Export filename"), check_modal_result)

  def on_close(self) -> None:
    self.dismiss()
