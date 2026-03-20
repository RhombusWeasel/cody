"""Sync todo DB helpers for skill scripts (subprocess / run_skill)."""
import os
import sys
import sqlite3

_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.abspath(os.path.join(_script_dir, "..", "..", ".."))
if _project_root not in sys.path:
  sys.path.insert(0, _project_root)

from utils.db import db_manager
from utils.paths import canonical_todo_scope, local_todo_scope_match_values


def db_path() -> str:
  return db_manager.get_project_db_path()


def add_todo(label: str, scope: str, todo_text: str, deadline: str | None) -> dict:
  scope = canonical_todo_scope(scope)
  conn = sqlite3.connect(db_path())
  try:
    cur = conn.cursor()
    cur.execute(
      "INSERT INTO todos (label, scope, todo_text, deadline) VALUES (?, ?, ?, ?)",
      (label, scope, todo_text, deadline),
    )
    conn.commit()
    return {"status": "success", "id": cur.lastrowid}
  except Exception as e:
    return {"status": "error", "message": str(e)}
  finally:
    conn.close()


def list_todos(scope: str | None, status: str | None) -> list | dict:
  query = (
    "SELECT id, label, scope, todo_text, creation_time, deadline, status, updated_at "
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
  conn = sqlite3.connect(db_path())
  try:
    cur = conn.cursor()
    cur.execute(query, tuple(params))
    rows = cur.fetchall()
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
      }
      for r in rows
    ]
  except Exception as e:
    return {"status": "error", "message": str(e)}
  finally:
    conn.close()


def update_status(todo_id: int, status: str) -> dict:
  conn = sqlite3.connect(db_path())
  try:
    cur = conn.cursor()
    cur.execute(
      "UPDATE todos SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
      (status, todo_id),
    )
    if cur.rowcount < 1:
      cur.execute("SELECT 1 FROM todos WHERE id = ?", (todo_id,))
      if not cur.fetchone():
        return {"status": "error", "message": f"No todo with id {todo_id}"}
    conn.commit()
    return {"status": "success"}
  except Exception as e:
    return {"status": "error", "message": str(e)}
  finally:
    conn.close()


def edit_todo(todo_id: int, label: str, todo_text: str, deadline: str | None) -> dict:
  conn = sqlite3.connect(db_path())
  try:
    cur = conn.cursor()
    cur.execute(
      """
      UPDATE todos
      SET label = ?, todo_text = ?, deadline = ?, updated_at = CURRENT_TIMESTAMP
      WHERE id = ?
      """,
      (label, todo_text, deadline, todo_id),
    )
    if cur.rowcount < 1:
      cur.execute("SELECT 1 FROM todos WHERE id = ?", (todo_id,))
      if not cur.fetchone():
        return {"status": "error", "message": f"No todo with id {todo_id}"}
    conn.commit()
    return {"status": "success"}
  except Exception as e:
    return {"status": "error", "message": str(e)}
  finally:
    conn.close()


def delete_todo(todo_id: int) -> dict:
  conn = sqlite3.connect(db_path())
  try:
    cur = conn.cursor()
    cur.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
    if cur.rowcount < 1:
      return {"status": "error", "message": f"No todo with id {todo_id}"}
    conn.commit()
    return {"status": "success"}
  except Exception as e:
    return {"status": "error", "message": str(e)}
  finally:
    conn.close()
