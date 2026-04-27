from dataclasses import dataclass, field
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
  thoughts: str | None = None  # reasoning/thinking content from the model


@dataclass
class TokenUsage:
  """Token usage statistics from a provider response."""
  prompt_tokens: int = 0
  completion_tokens: int = 0
  total_tokens: int = 0
  context_window: int = 0  # max context size (num_ctx or model limit)

  @property
  def context_used_pct(self) -> float:
    """Percentage of the context window used by the prompt."""
    if self.context_window <= 0:
      return 0.0
    return round(self.prompt_tokens / self.context_window * 100, 1)


@dataclass
class ChatResponse:
  """Normalized chat response compatible with ollama.ChatResponse shape."""
  message: Message
  usage: TokenUsage | None = None


@dataclass
class StreamChunk:
  """A single chunk from a streaming response."""
  content: str = ""
  thoughts: str | None = None  # reasoning/thinking delta for this chunk
  done: bool = False
  usage: TokenUsage | None = None


class BaseProvider(Protocol):
  def chat(
    self,
    model: str,
    messages: list[dict],
    tools: list | None = None,
    options: dict | None = None,
  ) -> ChatResponse:
    ...

  def stream_chat(
    self,
    model: str,
    messages: list[dict],
    tools: list | None = None,
    options: dict | None = None,
  ) -> list[StreamChunk]:
    """Stream a chat response, yielding chunks as they arrive.
    Returns a list of StreamChunk objects for compatibility with synchronous callers.
    """
    ...
