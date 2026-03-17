from dataclasses import dataclass
from typing import Protocol


class ToolCall:
  """Tool call with id, function.name and function.arguments for consumer compatibility."""

  def __init__(self, name: str, arguments: dict | str, id: str | None = None):
    self.id = id or ""
    self.function = type("Fn", (), {"name": name, "arguments": arguments or {}})()


@dataclass
class Message:
  content: str
  tool_calls: list[ToolCall] | None = None


@dataclass
class ChatResponse:
  """Normalized chat response compatible with ollama.ChatResponse shape."""
  message: Message


class BaseProvider(Protocol):
  def chat(
    self,
    model: str,
    messages: list[dict],
    tools: list | None = None,
    options: dict | None = None,
  ) -> ChatResponse:
    ...
