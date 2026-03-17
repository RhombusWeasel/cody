"""Convert Python callables to OpenAI-compatible tool schema."""
import inspect
import re
from typing import Callable, Any


def _py_type_to_json(t: type) -> str:
  m = {str: "string", int: "integer", float: "number", bool: "boolean", list: "array", dict: "object"}
  return m.get(t, "string")


def _parse_docstring_args(doc: str) -> dict[str, str]:
  """Extract Args section param descriptions from Google-style docstring."""
  result = {}
  in_args = False
  for line in (doc or "").split("\n"):
    stripped = line.strip()
    if stripped.startswith("Args:"):
      in_args = True
      continue
    if in_args:
      if stripped and not stripped.startswith(" ") and ":" in stripped:
        break
      match = re.match(r"(\w+):\s*(.+)", stripped)
      if match:
        result[match.group(1)] = match.group(2).strip()
  return result


def callable_to_openai_schema(func: Callable[..., Any]) -> dict:
  """Convert a Python function to OpenAI tool schema."""
  sig = inspect.signature(func)
  params = {}
  required = []
  arg_descs = _parse_docstring_args(func.__doc__ or "")
  for name, param in sig.parameters.items():
    if name == "self":
      continue
    anno = param.annotation
    if anno is inspect.Parameter.empty:
      anno = str
    params[name] = {
      "type": _py_type_to_json(anno) if isinstance(anno, type) else "string",
      "description": arg_descs.get(name, ""),
    }
    if param.default is inspect.Parameter.empty:
      required.append(name)
  return {
    "type": "function",
    "function": {
      "name": func.__name__,
      "description": (func.__doc__ or "").split("\n")[0].strip(),
      "parameters": {
        "type": "object",
        "properties": params,
        "required": required,
      },
    },
  }


def callables_to_openai_tools(funcs: list[Callable[..., Any]]) -> list[dict]:
  """Convert list of callables to OpenAI tools array."""
  return [callable_to_openai_schema(f) for f in funcs]
