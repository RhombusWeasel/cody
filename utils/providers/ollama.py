import json

from ollama import Client
from utils.providers.base import ChatResponse, Message, ToolCall


def _normalize_messages_for_ollama(messages: list[dict]) -> list[dict]:
  """Ollama's client validates messages with Pydantic; tool_calls must be dicts, not our ToolCall."""
  out: list[dict] = []
  for m in messages:
    if not isinstance(m, dict):
      out.append(m)
      continue
    m = dict(m)
    if m.get("role") != "assistant":
      out.append(m)
      continue
    raw_tcs = m.get("tool_calls")
    if not raw_tcs:
      out.append(m)
      continue
    fixed: list[dict] = []
    for tc in raw_tcs:
      if isinstance(tc, ToolCall):
        name = tc.function.name
        args = tc.function.arguments
        if isinstance(args, str):
          try:
            args = json.loads(args) if args.strip() else {}
          except json.JSONDecodeError:
            args = {}
        elif not isinstance(args, dict):
          args = {}
        fixed.append({"function": {"name": name, "arguments": args}})
      elif isinstance(tc, dict):
        fn = tc.get("function") or {}
        name = fn.get("name", "")
        args = fn.get("arguments", {})
        if isinstance(args, str):
          try:
            args = json.loads(args) if args.strip() else {}
          except json.JSONDecodeError:
            args = {}
        elif not isinstance(args, dict):
          args = {}
        fixed.append({"function": {"name": name, "arguments": args}})
      else:
        fixed.append(tc)
    m["tool_calls"] = fixed
    out.append(m)
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
      "messages": _normalize_messages_for_ollama(messages),
      "options": options,
    }
    if tools:
      kwargs["tools"] = tools
    resp = self._client.chat(**kwargs)
    tool_calls = None
    if resp.message.tool_calls:
      tool_calls = [
        ToolCall(
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
