"""Sync todo DB helpers for skill scripts (subprocess / run_skill)."""
import json
import os
import sys

_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.abspath(os.path.join(_script_dir, "..", "..", ".."))
if _project_root not in sys.path:
  sys.path.insert(0, _project_root)

from utils.db import db_manager
from utils.paths import canonical_todo_scope, local_todo_scope_match_values

_UNSET = object()


def db_path() -> str:
  return db_manager.get_project_db_path()


def normalize_comments_json(s: str) -> tuple[str | None, str | None]:
  """Validate JSON array of strings; return (serialized_json, error_message)."""
  raw = (s or "").strip()
  if not raw:
    raw = "[]"
  try:
    data = json.loads(raw)
  except json.JSONDecodeError as e:
    return None, f"invalid JSON: {e}"
  if not isinstance(data, list):
    return None, "comments must be a JSON array"
  for i, item in enumerate(data):
    if not isinstance(item, str):
      return None, f"comments[{i}] must be a string"
  return json.dumps(data), None


def add_todo(
  label: str,
  scope: str,
  todo_text: str,
  deadline: str | None,
  comments: str | None = None,
) -> dict:
  scope = canonical_todo_scope(scope)
  comments_json = "[]"
  if comments is not None:
    enc, err = normalize_comments_json(comments)
    if err:
      return {"status": "error", "message": err}
    comments_json = enc
  p = db_path()
  try:
    db_manager.execute_sync(
      p,
      "INSERT INTO todos (label, scope, todo_text, deadline, comments) VALUES (?, ?, ?, ?, ?)",
      (label, scope, todo_text, deadline, comments_json),
    )
    _, rows = db_manager.execute_sync(p, "SELECT last_insert_rowid()", ())
    return {"status": "success", "id": rows[0][0]}
  except Exception as e:
    return {"status": "error", "message": str(e)}


def list_todos(scope: str | None, status: str | None) -> list | dict:
  query = (
    "SELECT id, label, scope, todo_text, creation_time, deadline, status, updated_at, "
    "completion_note, completion_date, comments "
    "FROM todos WHERE 1=1"
  )
  params: list = []
  if scope:
    if scope == "global":
      query += " AND scope = ?"
      params.append("global")
    else:
      aliases = local_todo_scope_match_values(scope)
      query += f' AND scope IN ({",".join("?" * len(aliases))})'
      params.extend(aliases)
  if status:
    query += " AND status = ?"
    params.append(status)
  query += " ORDER BY creation_time DESC"
  p = db_path()
  try:
    _, rows = db_manager.execute_sync(p, query, tuple(params))
    return [
      {
        "id": r[0],
        "label": r[1],
        "scope": r[2],
        "todo_text": r[3],
        "creation_time": r[4],
        "deadline": r[5],
        "status": r[6],
        "updated_at": r[7],
        "completion_note": r[8],
        "completion_date": r[9],
        "comments": r[10],
      }
      for r in rows
    ]
  except Exception as e:
    return {"status": "error", "message": str(e)}


def update_status(
  todo_id: int,
  status: str,
  completion_note: str | None = None,
  completion_date: str | None = None,
) -> dict:
  if status == "completed":
    note = (completion_note or "").strip()
    if not note:
      return {
        "status": "error",
        "message": "completion_note is required (non-empty) when marking a task completed",
      }
    completion_note = note
  p = db_path()
  try:
    if status == "pending":
      db_manager.execute_sync(
        p,
        """
        UPDATE todos
        SET status = ?, completion_note = NULL, completion_date = NULL,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (status, todo_id),
      )
    else:
      db_manager.execute_sync(
        p,
        """
        UPDATE todos
        SET status = ?, completion_note = ?, completion_date = COALESCE(?, CURRENT_TIMESTAMP),
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (status, completion_note, completion_date, todo_id),
      )
    _, chg = db_manager.execute_sync(p, "SELECT changes()", ())
    n = chg[0][0] if chg else 0
    if n < 1:
      _, ex = db_manager.execute_sync(p, "SELECT 1 FROM todos WHERE id = ?", (todo_id,))
      if not ex:
        return {"status": "error", "message": f"No todo with id {todo_id}"}
    return {"status": "success"}
  except Exception as e:
    return {"status": "error", "message": str(e)}


def edit_todo(
  todo_id: int,
  label: str,
  todo_text: str,
  deadline: str | None,
  *,
  comments=_UNSET,
  completion_note=_UNSET,
  completion_date=_UNSET,
) -> dict:
  sets = ["label = ?", "todo_text = ?", "deadline = ?", "updated_at = CURRENT_TIMESTAMP"]
  vals: list = [label, todo_text, deadline]
  if comments is not _UNSET:
    enc, err = normalize_comments_json(comments)
    if err:
      return {"status": "error", "message": err}
    sets.append("comments = ?")
    vals.append(enc)
  if completion_note is not _UNSET:
    sets.append("completion_note = ?")
    vals.append(completion_note)
  if completion_date is not _UNSET:
    sets.append("completion_date = ?")
    vals.append(completion_date)
  vals.append(todo_id)
  p = db_path()
  try:
    q = f"UPDATE todos SET {', '.join(sets)} WHERE id = ?"
    db_manager.execute_sync(p, q, tuple(vals))
    _, chg = db_manager.execute_sync(p, "SELECT changes()", ())
    n = chg[0][0] if chg else 0
    if n < 1:
      _, ex = db_manager.execute_sync(p, "SELECT 1 FROM todos WHERE id = ?", (todo_id,))
      if not ex:
        return {"status": "error", "message": f"No todo with id {todo_id}"}
    return {"status": "success"}
  except Exception as e:
    return {"status": "error", "message": str(e)}


def append_todo_comment(todo_id: int, text: str) -> dict:
  p = db_path()
  try:
    _, rows = db_manager.execute_sync(p, "SELECT comments FROM todos WHERE id = ?", (todo_id,))
    if not rows:
      return {"status": "error", "message": f"No todo with id {todo_id}"}
    raw = rows[0][0]
    enc, err = normalize_comments_json(raw if raw else "[]")
    if err:
      return {"status": "error", "message": f"stored comments invalid: {err}"}
    data = json.loads(enc)
    data.append(text)
    new_json = json.dumps(data)
    db_manager.execute_sync(
      p,
      "UPDATE todos SET comments = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
      (new_json, todo_id),
    )
    return {"status": "success"}
  except Exception as e:
    return {"status": "error", "message": str(e)}


def delete_todo(todo_id: int) -> dict:
  p = db_path()
  try:
    db_manager.execute_sync(p, "DELETE FROM todos WHERE id = ?", (todo_id,))
    _, chg = db_manager.execute_sync(p, "SELECT changes()", ())
    n = chg[0][0] if chg else 0
    if n < 1:
      return {"status": "error", "message": f"No todo with id {todo_id}"}
    return {"status": "success"}
  except Exception as e:
    return {"status": "error", "message": str(e)}
