import json

from ollama import Client
from utils.providers.base import ChatResponse, Message, ToolCall as ProviderToolCall


def _tool_call_to_ollama_dict(tc):
  """Ollama's client validates messages with its own ToolCall model; our ProviderToolCall must become dicts."""
  if isinstance(tc, ProviderToolCall):
    name = tc.function.name
    args = tc.function.arguments
  elif isinstance(tc, dict):
    fn = tc.get("function") or {}
    name = fn.get("name", "")
    args = fn.get("arguments")
  else:
    if hasattr(tc, "model_dump"):
      return tc.model_dump()
    fn = getattr(tc, "function", None)
    name = getattr(fn, "name", "") if fn is not None else ""
    args = getattr(fn, "arguments", None) if fn is not None else None
  if args is None:
    args = {}
  if isinstance(args, str):
    args = json.loads(args) if args else {}
  return {"function": {"name": name, "arguments": dict(args)}}


def _messages_for_ollama_client(messages: list[dict]) -> list[dict]:
  out = []
  for msg in messages:
    tcs = msg.get("tool_calls")
    if not tcs:
      out.append(msg)
      continue
    out.append({**msg, "tool_calls": [_tool_call_to_ollama_dict(tc) for tc in tcs]})
  return out


class OllamaProvider:
  def __init__(self):
    self._client = Client()

  def chat(
    self,
    model: str,
    messages: list[dict],
    tools: list | None = None,
    options: dict | None = None,
  ) -> ChatResponse:
    kwargs = {
      "model": model,
      "messages": _messages_for_ollama_client(messages),
      "options": options,
    }
    if tools:
      kwargs["tools"] = tools
    resp = self._client.chat(**kwargs)
    tool_calls = None
    if resp.message.tool_calls:
      tool_calls = [
        ProviderToolCall(
          tc.function.name,
          tc.function.arguments,
          id=getattr(tc, "id", None) or f"call_{i}",
        )
        for i, tc in enumerate(resp.message.tool_calls)
      ]
    return ChatResponse(
      message=Message(
        content=resp.message.content or "",
        tool_calls=tool_calls,
      )
    )
