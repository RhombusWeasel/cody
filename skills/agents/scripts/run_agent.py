import sys
import os
import sqlite3
import argparse
import asyncio
import json

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..', '..', '..'))
if project_root not in sys.path:
  sys.path.insert(0, project_root)

import utils.fs as fs
from utils.db import db_manager
from utils.cfg_man import cfg
from utils.tool import get_tools
from utils.agent import TaskAgent


def _load_agent(name: str) -> dict | None:
  conn = sqlite3.connect(db_manager.get_project_db_path())
  cursor = conn.cursor()
  cursor.execute(
    'SELECT name, description, system_prompt, tool_groups, provider, model FROM agents WHERE name = ?',
    (name,)
  )
  row = cursor.fetchone()
  conn.close()
  if not row:
    return None
  return {
    'name': row[0],
    'description': row[1],
    'system_prompt': row[2],
    'tool_groups': json.loads(row[3]) if row[3] else [],
    'provider': row[4],
    'model': row[5],
  }


async def run(agent: dict, task: str) -> str:
  tool_groups = agent['tool_groups']
  tools = get_tools(tool_groups) if tool_groups else get_tools()

  if agent.get('provider'):
    cfg.set('session.provider', agent['provider'])
  if agent.get('model'):
    provider_key = agent.get('provider') or cfg.get('session.provider', 'ollama')
    cfg.set(f'providers.{provider_key}.model', agent['model'])

  task_agent = TaskAgent(agent['system_prompt'] or '', tools)
  return await task_agent.run(task)


def main():
  parser = argparse.ArgumentParser(description='Run a named sub-agent with a task.')
  parser.add_argument('--name', required=True, help='Agent name')
  parser.add_argument('--task', required=True, help='Task description')
  parser.add_argument('--working-directory', default=None, help='Working directory context')
  args = parser.parse_args()

  working_dir = args.working_directory or os.getcwd()
  cfg.set('session.working_directory', working_dir)

  fs.load_folder(os.path.join(project_root, 'tools'), '.py')

  global_tools = os.path.join(os.path.expanduser('~'), '.agents', 'tools')
  if os.path.exists(global_tools):
    fs.load_folder(global_tools, '.py')

  local_tools = os.path.join(working_dir, '.agents', 'tools')
  if os.path.exists(local_tools):
    fs.load_folder(local_tools, '.py')

  agent = _load_agent(args.name)
  if not agent:
    print(f"Error: agent '{args.name}' not found.")
    sys.exit(1)

  result = asyncio.run(run(agent, args.task))
  print(result)


if __name__ == '__main__':
  main()
