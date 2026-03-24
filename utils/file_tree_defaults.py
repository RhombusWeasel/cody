"""Default file tree UI config; import for register_default_config side effect."""
from utils.cfg_man import register_default_config

register_default_config({
  "file_tree": {
    "name_exclude_patterns": ["^__pycache__$"],
  },
})
