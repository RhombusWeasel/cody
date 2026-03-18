"""Nerd Font icon codepoints for consistent UI across components."""

# Sidebar Headers
CHATS = ""
FILE_SYSTEM = ""
GIT = ""
DB = ""
SKILLS = ""
SETTINGS = ""

# Selection
CHECKED = "󰄲"
UNCHECKED = ""
SELECT_ALL = "󰄸"
CLEAR_SELECTION = "󰄷"

# Actions
DELETE = "󰛌"
EDIT = ""
NEW_FILE = ""
NEW_FOLDER = ""
RUN = ""
EXPORT_CSV = "󰈇"
OPEN_EXTERNAL = "󰏌"

# Database
DATABASE = DB
REFRESH = ""

# Tree / file browser
FOLDER = ""  # nf-cod-folder
FILE = ""  # nf-cod-file
EXPAND_DOWN = "󰧗"  # nf-cod-chevron_down
EXPAND_RIGHT = "󰧛"  # nf-cod-chevron_right

# Git tree
GIT_BRANCH = ""  # nf-cod-git_branch
GIT_COMMIT = ""  # nf-cod-git_commit
GIT_CHANGE = ""  # nf-cod-diff
GIT_DISCARD = ""  # nf-cod-discard
GIT_IGNORE = ""  # nf-cod-file_symlink_file
GIT_CHERRY_PICK = ""  # nf-fae-cherry
GIT_ADD = ""  # nf-fa-plus
GIT_UNSTAGE = ""  # nf-fa-minus

# Database tree
DB_TABLE = ""  # nf-fa-table
DB_VIEW = "󱤢"  # nf-md-database_eye_outline
DB_TRIGGER = "󱘽"  # nf-cod-zap

# File type icons (devicons)
FILE_ICONS = {
  ".py": "\uE73C",
  ".lua": "\ue826",
  ".js": "\uf2ef",
  ".ts": "\uE69D",
  ".html": "\uE60E",
  ".css": "\uE614",
  ".json": "\uE60B",
  ".md": "\uE609",
  ".yaml": "\uE8EB",
  ".yml": "\uE8EB",
  ".toml": "\uE6B2",
  ".rs": "\uE7A8",
  ".go": "\uE627",
  ".c": "\uE61E",
  ".cpp": "\uE61D",
  ".sh": "\uE760",
  ".png": "\uF1C5",
  ".jpg": "\uF1C5",
  ".jpeg": "\uF1C5",
  ".gif": "\uF1C5",
  ".bmp": "\uF1C5",
  ".tiff": "\uF1C5",
  ".ico": "\uF1C5",
  ".webp": "\uF1C5",
  ".svg": "\uF1C5",
}

# Default icon set for GenericTree - subclasses can override via icon_set param
DEFAULT_ICON_SET = {
  "folder": FOLDER,
  "file": FILE,
  "database": DATABASE,
  "git": GIT,
  "skill": SKILLS,
}

# Preset icon sets for domain-specific trees
DB_ICON_SET = {
  **DEFAULT_ICON_SET,
  "folder": FOLDER,
  "file": FILE,
  "database": DATABASE,
  "table": DB_TABLE,
  "view": DB_VIEW,
  "trigger": DB_TRIGGER,
}

GIT_ICON_SET = {
  **DEFAULT_ICON_SET,
  "folder": FOLDER,
  "file": FILE,
  "git": GIT,
  "branch": GIT_BRANCH,
  "change": GIT_CHANGE,
  "commit": GIT_COMMIT,
}

SKILL_ICON_SET = {
  **DEFAULT_ICON_SET,
  "folder": FOLDER,
  "file": FILE,
  "skill": SKILLS,
}
