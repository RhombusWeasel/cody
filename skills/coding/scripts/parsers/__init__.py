from pathlib import Path
from typing import Optional


class ParseResult:
    """Result of parsing a file for structural elements."""

    def __init__(self, file_path: str, language: str, total_lines: int):
        self.file_path = file_path
        self.language = language
        self.total_lines = total_lines
        self.imports: list[dict] = []
        self.classes: list[dict] = []
        self.functions: list[dict] = []
        self.variables: list[dict] = []
        self.sections: list[dict] = []

    def to_summary(self) -> str:
        """Render a human-readable summary / table of contents."""
        lines = []
        lines.append(f"\U0001f4c4 {self.file_path} \u2014 {self.total_lines} lines ({self.language})")
        lines.append("\u2500" * 60)

        if self.imports:
            lines.append(f"\n\U0001f4e6 Imports ({len(self.imports)}):")
            for imp in self.imports[:10]:
                lines.append(f"  Line {imp['line']:>6} \u2502 {imp['text']}")
            if len(self.imports) > 10:
                lines.append(f"  \u2026 and {len(self.imports) - 10} more")

        if self.classes:
            lines.append(f"\n\U0001f3db\ufe0f  Classes ({len(self.classes)}):")
            for cls in self.classes:
                deco = f" {' '.join(cls['decorators'])}" if cls.get('decorators') else ""
                doc = f"  # {cls['docstring'][:60]}\u2026" if cls.get('docstring') else ""
                lines.append(f"  Line {cls['line']:>6} \u2502{deco} class {cls['name']}{doc}")

        if self.functions:
            lines.append(f"\n\u2699\ufe0f  Functions ({len(self.functions)}):")
            for fn in self.functions:
                prefix = "async " if fn.get('async') else ""
                deco = f" {' '.join(fn['decorators'])}" if fn.get('decorators') else ""
                parent = f" (in {fn['parent']})" if fn.get('parent') else ""
                doc = f"  # {fn['docstring'][:60]}\u2026" if fn.get('docstring') else ""
                lines.append(f"  Line {fn['line']:>6} \u2502{deco} {prefix}def {fn['name']}{parent}{doc}")

        if self.variables:
            lines.append(f"\n\U0001f4cb Top-level variables ({len(self.variables)}):")
            for var in self.variables[:15]:
                lines.append(f"  Line {var['line']:>6} \u2502 {var['name']} = {var['value_preview'][:50]}")
            if len(self.variables) > 15:
                lines.append(f"  \u2026 and {len(self.variables) - 15} more")

        return "\n".join(lines)

    def to_json(self) -> dict:
        """Return a JSON-serializable dict."""
        return {
            "file_path": self.file_path,
            "language": self.language,
            "total_lines": self.total_lines,
            "imports": self.imports,
            "classes": self.classes,
            "functions": self.functions,
            "variables": self.variables,
            "sections": self.sections,
        }


class BaseParser:
    """Base class for language-specific parsers."""

    language: str = "unknown"
    extensions: tuple[str, ...] = ()

    def parse(self, file_path: str, content: str) -> ParseResult:
        """Parse file content and return a ParseResult."""
        raise NotImplementedError


# Parser registry

_parsers: dict[str, BaseParser] = {}


def register_parser(parser: BaseParser) -> None:
    """Register a parser instance."""
    for ext in parser.extensions:
        _parsers[ext.lower()] = parser


def get_parser(file_path: str) -> Optional[BaseParser]:
    """Get the appropriate parser for a file path by extension."""
    ext = Path(file_path).suffix.lower()
    return _parsers.get(ext)


# Import language parsers to trigger auto-registration
from parsers import python_parser  # noqa: F401


def list_parsers() -> list[str]:
    """List all registered parser languages."""
    return sorted(set(p.language for p in _parsers.values()))
