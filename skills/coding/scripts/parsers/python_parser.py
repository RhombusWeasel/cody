import ast
from typing import Optional

from parsers import BaseParser, ParseResult


def _get_docstring(node: ast.AST) -> Optional[str]:
    """Extract docstring from a node if present."""
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
        if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant):
            if isinstance(node.body[0].value.value, str):
                return node.body[0].value.value.strip()
    return None


def _get_decorator_names(node: ast.AST) -> list[str]:
    """Get decorator names as strings."""
    if hasattr(node, 'decorator_list'):
        names = []
        for dec in node.decorator_list:
            if isinstance(dec, ast.Name):
                names.append(f"@{dec.id}")
            elif isinstance(dec, ast.Attribute):
                names.append(f"@{ast.unparse(dec)}")
            elif isinstance(dec, ast.Call):
                if isinstance(dec.func, ast.Name):
                    names.append(f"@{dec.func.id}(...)")
                elif isinstance(dec.func, ast.Attribute):
                    names.append(f"@{ast.unparse(dec.func)}(...)")
                else:
                    names.append(f"@{ast.unparse(dec)[:40]}")
            else:
                names.append(f"@{ast.unparse(dec)[:40]}")
        return names
    return []


def _value_preview(node: ast.AST, max_len: int = 50) -> str:
    """Get a short preview of a value."""
    try:
        text = ast.unparse(node)
        if len(text) > max_len:
            return text[:max_len] + "..."
        return text
    except Exception:
        return "<complex>"


class PythonParser(BaseParser):
    """AST-based parser for Python files."""

    language = "Python"
    extensions = (".py",)

    def parse(self, file_path: str, content: str) -> ParseResult:
        total_lines = len(content.split("\n"))
        result = ParseResult(file_path, self.language, total_lines)

        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            result.imports.append({"line": 0, "text": f"[Parse error: {e}]"})
            return result

        # Module-level docstring
        mod_doc = _get_docstring(tree)
        if mod_doc:
            result.sections.append({
                "line": 1,
                "name": "Module docstring",
                "kind": "docstring",
                "end_line": 1 + mod_doc.count("\n"),
            })

        # Walk the AST
        for node in ast.walk(tree):
            # Imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    result.imports.append({
                        "line": node.lineno,
                        "text": f"import {alias.name}" + (f" as {alias.asname}" if alias.asname else ""),
                    })
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                names = []
                for alias in node.names:
                    name = alias.name + (f" as {alias.asname}" if alias.asname else "")
                    names.append(name)
                result.imports.append({
                    "line": node.lineno,
                    "text": f"from {module} import {', '.join(names)}",
                })

            # Class definitions (top-level only)
            if isinstance(node, ast.ClassDef):
                for parent in ast.walk(tree):
                    if isinstance(parent, ast.Module):
                        if node in parent.body:
                            doc = _get_docstring(node)
                            decos = _get_decorator_names(node)
                            end_line = _find_end_line(content, node.lineno)
                            result.classes.append({
                                "line": node.lineno,
                                "name": node.name,
                                "end_line": end_line,
                                "docstring": doc,
                                "decorators": decos,
                            })
                            result.sections.append({
                                "line": node.lineno,
                                "name": node.name,
                                "kind": "class",
                                "end_line": end_line,
                            })
                            break

            # Function definitions
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                is_async = isinstance(node, ast.AsyncFunctionDef)
                doc = _get_docstring(node)
                decos = _get_decorator_names(node)
                end_line = _find_end_line(content, node.lineno)

                # Determine parent
                parent_name = None
                for parent in ast.walk(tree):
                    if isinstance(parent, ast.ClassDef):
                        if node in parent.body:
                            parent_name = parent.name
                            break

                fn_entry = {
                    "line": node.lineno,
                    "name": node.name,
                    "end_line": end_line,
                    "docstring": doc,
                    "decorators": decos,
                    "async": is_async,
                    "parent": parent_name,
                }
                result.functions.append(fn_entry)

                kind = "async def" if is_async else "def"
                section_name = f"{parent_name}.{node.name}" if parent_name else node.name
                result.sections.append({
                    "line": node.lineno,
                    "name": section_name,
                    "kind": kind,
                    "end_line": end_line,
                })

            # Top-level variable assignments
            if isinstance(node, ast.Assign):
                for parent in ast.walk(tree):
                    if isinstance(parent, ast.Module):
                        if node in parent.body:
                            for target in node.targets:
                                if isinstance(target, ast.Name):
                                    preview = _value_preview(node.value)
                                    result.variables.append({
                                        "line": node.lineno,
                                        "name": target.id,
                                        "value_preview": preview,
                                    })
                            break

            # AnnAssign (type-annotated assignments like `x: int = 5`)
            if isinstance(node, ast.AnnAssign):
                for parent in ast.walk(tree):
                    if isinstance(parent, ast.Module):
                        if node in parent.body:
                            if isinstance(node.target, ast.Name):
                                preview = _value_preview(node.value) if node.value else "<no value>"
                                result.variables.append({
                                    "line": node.lineno,
                                    "name": node.target.id,
                                    "value_preview": preview,
                                })
                            break

        return result


def _find_end_line(content: str, start_line: int) -> int:
    """Find the last line of a definition by tracking indentation."""
    lines = content.split("\n")
    if start_line > len(lines):
        return start_line

    # Get the indentation of the definition line
    def_line = lines[start_line - 1]
    base_indent = len(def_line) - len(def_line.lstrip())

    end = start_line
    for i in range(start_line, len(lines)):
        line = lines[i]
        stripped = line.strip()
        # Empty lines or comments at same/base indent level don't end the block
        if not stripped or stripped.startswith("#"):
            end = i + 1
            continue
        indent = len(line) - len(line.lstrip())
        if indent <= base_indent:
            break
        end = i + 1

    return end


# Auto-register
from parsers import register_parser
register_parser(PythonParser())
