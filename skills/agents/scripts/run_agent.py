import sys
import os
import argparse
import asyncio
import json

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..', '..', '..'))
if project_root not in sys.path:
  sys.path.insert(0, project_root)

import utils.fs as fs
from utils.db import db_manager
from utils.cfg_man import cfg, ensure_config_loaded
from utils.tool import get_tools
from utils.agent import TaskAgent


def _load_agent(name: str) -> dict | None:
  p = db_manager.get_project_db_path()
  _, rows = db_manager.execute_sync(
    p,
    "SELECT name, description, system_prompt, tool_groups, provider, model FROM agents WHERE name = ?",
    (name,),
  )
  if not rows:
    return None
  row = rows[0]
  return {
    "name": row[0],
    "description": row[1],
    "system_prompt": row[2],
    "tool_groups": json.loads(row[3]) if row[3] else [],
    "provider": row[4],
    "model": row[5],
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
  parser.add_argument(
    '--config-password-file',
    default=None,
    metavar='PATH',
    help='Read config decryption password from file (if using encrypted config).',
  )
  args = parser.parse_args()

  working_dir = os.path.abspath(args.working_directory or os.getcwd())
  ensure_config_loaded(working_dir, config_password_file=args.config_password_file)
  cfg.set('session.working_directory', working_dir)

  from utils.paths import get_tiered_paths
  for tool_path in get_tiered_paths('tools', working_dir):
    if os.path.exists(tool_path):
      fs.load_folder(tool_path, '.py')

  agent = _load_agent(args.name)
  if not agent:
    print(f"Error: agent '{args.name}' not found.")
    sys.exit(1)

  result = asyncio.run(run(agent, args.task))
  print(result)


if __name__ == '__main__':
  main()
