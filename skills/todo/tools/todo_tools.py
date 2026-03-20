import sqlite3
from utils.db import db_manager
from utils.cfg_man import cfg
from utils.paths import canonical_todo_scope, local_todo_scope_match_values

def _get_db_path():
    return db_manager.get_project_db_path()

async def add_todo(label: str, scope: str, todo_text: str, deadline: str = None) -> dict:
    """
    Add a new todo task.
    :param label: Short label or title for the task.
    :param scope: 'global' or the current working directory path.
    :param todo_text: Detailed description of the task.
    :param deadline: Optional deadline (e.g., 'YYYY-MM-DD').
    :return: The ID of the newly created task.
    """
    db_path = _get_db_path()
    query = '''
        INSERT INTO todos (label, scope, todo_text, deadline)
        VALUES (?, ?, ?, ?)
    '''
    try:
        scope = canonical_todo_scope(scope)
        await db_manager.execute(db_path, query, (label, scope, todo_text, deadline))
        # Get the last inserted id
        columns, rows = await db_manager.execute(db_path, "SELECT last_insert_rowid()", ())
        if rows:
            return {"status": "success", "id": rows[0][0]}
        return {"status": "success", "id": None}
    except Exception as e:
        return {"status": "error", "message": str(e)}

async def get_todos(scope: str = None, status: str = None) -> list:
    """
    Get a list of todos.
    :param scope: Optional scope to filter by ('global' or a directory path).
    :param status: Optional status to filter by ('pending' or 'completed').
    :return: A list of todo dictionaries.
    """
    db_path = _get_db_path()
    query = 'SELECT id, label, scope, todo_text, creation_time, deadline, status, updated_at FROM todos WHERE 1=1'
    params = []
    
    if scope:
        if scope == "global":
            query += " AND scope = ?"
            params.append("global")
        else:
            aliases = local_todo_scope_match_values(scope)
            query += f' AND scope IN ({",".join("?" * len(aliases))})'
            params.extend(aliases)
    if status:
        query += ' AND status = ?'
        params.append(status)
        
    query += ' ORDER BY creation_time DESC'
    
    try:
        columns, rows = await db_manager.execute(db_path, query, tuple(params))
        return [
            {
                "id": r[0], "label": r[1], "scope": r[2], "todo_text": r[3],
                "creation_time": r[4], "deadline": r[5], "status": r[6], "updated_at": r[7]
            }
            for r in rows
        ]
    except Exception as e:
        return [{"status": "error", "message": str(e)}]

async def update_todo_status(todo_id: int, status: str) -> dict:
    """
    Update the status of a todo task.
    :param todo_id: The ID of the task to update.
    :param status: 'pending' or 'completed'.
    :return: Status dictionary.
    """
    db_path = _get_db_path()
    query = '''
        UPDATE todos
        SET status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    '''
    try:
        await db_manager.execute(db_path, query, (status, todo_id))
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

async def edit_todo(todo_id: int, label: str, todo_text: str, deadline: str = None) -> dict:
    """
    Edit an existing todo task.
    :param todo_id: The ID of the task to edit.
    :param label: New label.
    :param todo_text: New text.
    :param deadline: New deadline.
    :return: Status dictionary.
    """
    db_path = _get_db_path()
    query = '''
        UPDATE todos
        SET label = ?, todo_text = ?, deadline = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    '''
    try:
        await db_manager.execute(db_path, query, (label, todo_text, deadline, todo_id))
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

async def delete_todo(todo_id: int) -> dict:
    """
    Delete a todo task.
    :param todo_id: The ID of the task to delete.
    :return: Status dictionary.
    """
    db_path = _get_db_path()
    query = 'DELETE FROM todos WHERE id = ?'
    try:
        await db_manager.execute(db_path, query, (todo_id,))
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
