tools = {}
groups = {}
enabled_tools = set()


def register_tool(label, func, tags=None):
  tools[label] = func
  enabled_tools.add(label)
  if tags is None:
    return tools[label]
  for key in tags:
    if key not in groups:
      groups[key] = []
    if label not in groups[key]:
      groups[key].append(label)
  return tools[label]


def get_group_tools(group_name):
  if group_name not in groups:
    return []
  return [tool_name for tool_name in groups[group_name] if tool_name in tools]


def is_tool_enabled(tool_name):
  return tool_name in enabled_tools


def toggle_tool(tool_name):
  if tool_name not in tools:
    return False
  if tool_name in enabled_tools:
    enabled_tools.remove(tool_name)
    return False
  enabled_tools.add(tool_name)
  return True


def set_tool_enabled(tool_name, enabled):
  if tool_name not in tools:
    return False
  if enabled:
    enabled_tools.add(tool_name)
  else:
    enabled_tools.discard(tool_name)
  return True


def is_group_enabled(group_name):
  group_tools = get_group_tools(group_name)
  if not group_tools:
    return False
  return all(tool_name in enabled_tools for tool_name in group_tools)


def is_group_partially_enabled(group_name):
  group_tools = get_group_tools(group_name)
  if not group_tools:
    return False
  enabled_count = len([name for name in group_tools if name in enabled_tools])
  return 0 < enabled_count < len(group_tools)


def set_group_enabled(group_name, enabled):
  group_tools = get_group_tools(group_name)
  for tool_name in group_tools:
    set_tool_enabled(tool_name, enabled)
  return len(group_tools)


def toggle_group(group_name):
  group_tools = get_group_tools(group_name)
  if not group_tools:
    return False
  should_enable = any(tool_name not in enabled_tools for tool_name in group_tools)
  set_group_enabled(group_name, should_enable)
  return should_enable


def get_tools(tags: list[str]=None):
  funcs = []
  if tags == None:
    tags = groups
  for group_name in tags:
    for tool_name in get_group_tools(group_name):
      if tool_name in enabled_tools:
        funcs.append(tools[tool_name])
  return funcs

def get_enabled_tool_functions():
  return [tools[tool_name] for tool_name in tools if tool_name in enabled_tools]


def execute_tool(name, args):
  if name not in tools:
    return False
  if name not in enabled_tools:
    return f"Tool '{name}' is disabled."
  return tools[name](**args)


def get_tool_state_snapshot():
  group_snapshot = tuple(
    (group_name, tuple(sorted(get_group_tools(group_name))))
    for group_name in sorted(groups)
  )
  return (
    tuple(sorted(tools.keys())),
    group_snapshot,
    tuple(sorted(enabled_tools)),
  )
