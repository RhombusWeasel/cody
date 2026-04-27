import re
from typing import Optional

from parsers import BaseParser, ParseResult


class LuaParser(BaseParser):
    """
    Regex-based parser for Lua files.

    This is an example parser to demonstrate how to add support for new languages.
    To add your own parser:
      1. Create a new file in scripts/parsers/
      2. Subclass BaseParser and implement parse()
      3. Set language name and file extensions
      4. Call register_parser(YourParser()) at module level
    """

    language = "Lua"
    extensions = (".lua", ".wlua")

    # Regex patterns for Lua structural elements
    _FUNCTION_PATTERN = re.compile(
        r'^\s*(?:local\s+)?function\s+(?:[\w.]+:)?(\w+)\s*\('
    )
    _LOCAL_FUNCTION_PATTERN = re.compile(
        r'^\s*local\s+(\w+)\s*=\s*function\s*\('
    )
    _METHOD_PATTERN = re.compile(
        r'^\s*function\s+([\w.]+):(\w+)\s*\('
    )
    _VARIABLE_PATTERN = re.compile(
        r'^\s*local\s+(\w+)\s*=\s*(.*?)\s*(?:--.*)?$'
    )
    _MODULE_PATTERN = re.compile(
        r'^\s*(?:require|import)\s+["\']([^"\']+)["\']'
    )

    def parse(self, file_path: str, content: str) -> ParseResult:
        total_lines = len(content.split("\n"))
        result = ParseResult(file_path, self.language, total_lines)

        lines = content.split("\n")
        i = 0

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            line_num = i + 1

            # Skip comments and empty lines
            if not stripped or stripped.startswith("--"):
                i += 1
                continue

            # Module imports (require)
            mod_match = self._MODULE_PATTERN.match(stripped)
            if mod_match:
                result.imports.append({
                    "line": line_num,
                    "text": stripped.strip(),
                })
                i += 1
                continue

            # Method definitions (ClassName:method_name)
            method_match = self._METHOD_PATTERN.match(stripped)
            if method_match:
                class_name = method_match.group(1)
                method_name = method_match.group(2)
                end_line = self._find_block_end(lines, i)
                result.functions.append({
                    "line": line_num,
                    "name": f"{class_name}:{method_name}",
                    "end_line": end_line,
                    "docstring": None,
                    "decorators": [],
                    "async": False,
                    "parent": class_name,
                })
                result.sections.append({
                    "line": line_num,
                    "name": f"{class_name}:{method_name}",
                    "kind": "method",
                    "end_line": end_line,
                })
                i = end_line
                continue

            # Function definitions
            fn_match = self._FUNCTION_PATTERN.match(stripped)
            if fn_match:
                fn_name = fn_match.group(1)
                end_line = self._find_block_end(lines, i)
                result.functions.append({
                    "line": line_num,
                    "name": fn_name,
                    "end_line": end_line,
                    "docstring": None,
                    "decorators": [],
                    "async": False,
                    "parent": None,
                })
                result.sections.append({
                    "line": line_num,
                    "name": fn_name,
                    "kind": "function",
                    "end_line": end_line,
                })
                i = end_line
                continue

            # Local function assignments
            lf_match = self._LOCAL_FUNCTION_PATTERN.match(stripped)
            if lf_match:
                fn_name = lf_match.group(1)
                end_line = self._find_block_end(lines, i)
                result.functions.append({
                    "line": line_num,
                    "name": fn_name,
                    "end_line": end_line,
                    "docstring": None,
                    "decorators": [],
                    "async": False,
                    "parent": None,
                })
                result.sections.append({
                    "line": line_num,
                    "name": fn_name,
                    "kind": "function",
                    "end_line": end_line,
                })
                i = end_line
                continue

            # Variable assignments (local)
            var_match = self._VARIABLE_PATTERN.match(stripped)
            if var_match:
                var_name = var_match.group(1)
                value = var_match.group(2).strip()
                # Skip if it's actually a function (already caught above)
                if not value.startswith("function"):
                    result.variables.append({
                        "line": line_num,
                        "name": var_name,
                        "value_preview": value[:50],
                    })
                i += 1
                continue

            i += 1

        return result

    def _find_block_end(self, lines: list[str], start: int) -> int:
        """Find the end of a block by tracking indentation."""
        if start >= len(lines):
            return start

        # For one-liners (function on same line as end)
        def_line = lines[start]
        if "end" in def_line and def_line.count("end") >= def_line.count("function"):
            return start + 1

        end = start + 1
        depth = 0
        for i in range(start, len(lines)):
            stripped = lines[i].strip()
            if stripped.startswith("--"):
                continue
            # Track block depth
            depth += stripped.count("function") + stripped.count("then") + stripped.count("do") + stripped.count("{")
            depth -= stripped.count("end") + stripped.count("}")
            if depth <= 0 and i > start:
                end = i + 1
                break
            end = i + 1

        return end


# Auto-register
from parsers import register_parser
register_parser(LuaParser())
