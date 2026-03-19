import sys
import os
import sqlite3

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..', '..', '..'))
if project_root not in sys.path:
  sys.path.insert(0, project_root)

from utils.db import db_manager


def main():
  conn = sqlite3.connect(db_manager.get_project_db_path())
  cursor = conn.cursor()
  cursor.execute('SELECT name, description, provider, model FROM agents ORDER BY name')
  rows = cursor.fetchall()
  conn.close()

  if not rows:
    print("No agents defined. Create agents via the Agents sidebar tab.")
    return

  for name, description, provider, model in rows:
    provider_str = f" [{provider or 'default'}/{model or 'default'}]" if provider or model else ""
    print(f"{name}{provider_str}")
    if description:
      print(f"  {description}")
    print()


if __name__ == '__main__':
  main()
