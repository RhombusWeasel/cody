"""Nerd Font icon codepoints for consistent UI across components."""

# Sidebar Headers
CHATS = "\uea82"
FILE_SYSTEM = "\uea83"
GIT = "\ue5fb"
SKILLS = "\uf19d"
DB = "\uf472"
SETTINGS = "\ue690"

# Selection
CHECKED = "\u2611"  # ballot box with check
UNCHECKED = "\u2610"  # ballot box

# Actions
DELETE = "\uEA81"  # nf-cod-trash
EDIT = "\uEA73"  # nf-cod-edit
NEW_FILE = "\uEA7F"  # nf-cod-new_file
NEW_FOLDER = "\uEA80"  # nf-cod-new_folder
RUN = "\uEB9E"  # nf-cod-run_all
EXPORT_CSV = "\uE27C"  # nf-fae-file_export
OPEN_EXTERNAL = "\uEB14"  # nf-cod-link_external

# Database
DATABASE = "\uEACE"  # nf-cod-database
REFRESH = "\uEC0C"  # nf-cod-refresh

# Tree / file browser
FOLDER = "\uEA83"  # nf-cod-folder
FILE = "\uEA7B"  # nf-cod-file
EXPAND_DOWN = "\uEAB4"  # nf-cod-chevron_down
EXPAND_RIGHT = "\uEAB6"  # nf-cod-chevron_right

# Git tree
GIT_BRANCH = "\ue725"  # nf-cod-git_branch
GIT_COMMIT = "\ue729"  # nf-cod-git_commit
GIT_CHANGE = "\uec0c"  # nf-cod-diff

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
