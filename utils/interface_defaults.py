"""Default interface config; import for register_default_config side effect."""
from utils.cfg_man import register_default_config

register_default_config({
  "interface": {
    "sidebar_open_on_start": True,
    "show_system_messages": True,
    "show_tool_messages": True,
    "leader_key": "ctrl+space",
    "theme": "h4x0\u044f",
    "streaming": True,  # Use streaming chat (live token-by-token output)
  },
})
