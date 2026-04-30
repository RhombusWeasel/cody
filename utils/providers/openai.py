import json
from openai import OpenAI
from utils.cfg_man import cfg
from utils.providers.base import ChatResponse, Message, StreamChunk, ToolCall, TokenUsage
from utils.providers.tools import callables_to_openai_tools


def _to_openai_messages(messages: list[dict]) -> list[dict]:
  """Convert our message format to OpenAI API format."""
  out = []
  tool_idx = 0
  for m in messages:
    role = m.get("role")
    content = m.get("content", "")
    if role == "tool":
      tool_call_id = m.get("tool_call_id") or f"call_{tool_idx}"
      tool_idx += 1
      out.append({"role": "tool", "tool_call_id": tool_call_id, "content": content})
      continue
    if role == "assistant" and m.get("tool_calls"):
      msg = {"role": "assistant", "content": content or None}
      msg["tool_calls"] = [
        {
          "id": tc.id or f"call_{i}",
          "type": "function",
          "function": {
            "name": tc.function.name,
            "arguments": json.dumps(tc.function.arguments) if isinstance(tc.function.arguments, dict) else (tc.function.arguments or "{}"),
          },
        }
        for i, tc in enumerate(m["tool_calls"])
      ]
      out.append(msg)
    else:
      out.append({"role": role, "content": content})
  return out


def _resolve_api_key() -> str | None:
  """TUI sets cache via openai_vault; TaskAgent/CLI use cfg (or env via OpenAI())."""
  import utils.password_vault as password_vault
  from utils.providers.openai_vault import (
    OPENAI_VAULT_CREDENTIAL_ID,
    get_cached_openai_api_key,
    looks_like_placeholder_openai_api_key,
  )
  cached = get_cached_openai_api_key()
  if cached and not looks_like_placeholder_openai_api_key(cached):
    return cached
  cfg_key = (cfg.get("providers.openai.api_key") or "").strip()
  if cfg_key and not looks_like_placeholder_openai_api_key(cfg_key):
    return cfg_key
  vault_key = password_vault.get_secret(OPENAI_VAULT_CREDENTIAL_ID)
  if vault_key and not looks_like_placeholder_openai_api_key(vault_key):
    return vault_key
  return None


class OpenAIProvider:
  def chat(
    self,
    model: str,
    messages: list[dict],
    tools: list | None = None,
    options: dict | None = None,
  ) -> ChatResponse:
    api_key = _resolve_api_key()
    client = OpenAI(api_key=api_key) if api_key else OpenAI()
    opts = options or {}
    api_messages = _to_openai_messages(messages)
    kwargs = {
      "model": model,
      "messages": api_messages,
      "temperature": opts.get("temperature", 0.7),
      "max_tokens": opts.get("max_tokens"),
    }
    if tools:
      kwargs["tools"] = callables_to_openai_tools(tools)
      kwargs["tool_choice"] = "auto"
    resp = client.chat.completions.create(**{k: v for k, v in kwargs.items() if v is not None})
    msg = resp.choices[0].message
    tool_calls = None
    if msg.tool_calls:
      tool_calls = [
        ToolCall(
          tc.function.name,
          tc.function.arguments or "{}",
          id=tc.id,
        )
        for tc in msg.tool_calls
      ]
    usage = None
    if resp.usage:
      usage = TokenUsage(
        prompt_tokens=resp.usage.prompt_tokens or 0,
        completion_tokens=resp.usage.completion_tokens or 0,
        total_tokens=resp.usage.total_tokens or 0,
      )
    return ChatResponse(
      message=Message(
        content=msg.content or "",
        tool_calls=tool_calls,
      ),
      usage=usage,
    )

  def stream_chat(
    self,
    model: str,
    messages: list[dict],
    tools: list | None = None,
    options: dict | None = None,
  ) -> list[StreamChunk]:
    """Stream a chat response, capturing thoughts/reasoning content and tool calls."""
    api_key = _resolve_api_key()
    client = OpenAI(api_key=api_key) if api_key else OpenAI()
    opts = options or {}
    api_messages = _to_openai_messages(messages)
    kwargs = {
      "model": model,
      "messages": api_messages,
      "temperature": opts.get("temperature", 0.7),
      "max_tokens": opts.get("max_tokens"),
      "stream": True,
      "stream_options": {"include_usage": True},
    }
    if tools:
      kwargs["tools"] = callables_to_openai_tools(tools)
      kwargs["tool_choice"] = "auto"

    chunks: list[StreamChunk] = []
    thoughts_buffer = []
    # Accumulate tool call deltas across chunks
    tool_call_deltas: dict[int, dict] = {}

    for stream_chunk in client.chat.completions.create(**{k: v for k, v in kwargs.items() if v is not None}):
      delta = stream_chunk.choices[0].delta if stream_chunk.choices else None
      if delta is None:
        continue

      content = delta.content or ""
      thoughts = None

      # OpenAI may include reasoning content in the 'reasoning' field
      if hasattr(delta, "reasoning") and delta.reasoning:
        thoughts = delta.reasoning
        thoughts_buffer.append(delta.reasoning)

      # Accumulate tool call deltas
      if delta.tool_calls:
        for tc_delta in delta.tool_calls:
          idx = tc_delta.index
          if idx not in tool_call_deltas:
            tool_call_deltas[idx] = {
              "id": tc_delta.id or "",
              "function_name": "",
              "arguments": "",
            }
          if tc_delta.id:
            tool_call_deltas[idx]["id"] = tc_delta.id
          if tc_delta.function:
            if tc_delta.function.name:
              tool_call_deltas[idx]["function_name"] = tc_delta.function.name
            if tc_delta.function.arguments:
              tool_call_deltas[idx]["arguments"] += tc_delta.function.arguments

      sc = StreamChunk(
        content=content,
        thoughts=thoughts,
        done=False,
      )

      # Check for usage in the final chunk
      if stream_chunk.usage:
        u = stream_chunk.usage
        sc.usage = TokenUsage(
          prompt_tokens=u.prompt_tokens or 0,
          completion_tokens=u.completion_tokens or 0,
          total_tokens=u.total_tokens or 0,
        )
        sc.done = True

      chunks.append(sc)

    # If we accumulated tool calls, attach them to the final chunk
    if tool_call_deltas:
      tool_calls = [
        ToolCall(
          tc_data["function_name"],
          tc_data["arguments"],
          id=tc_data["id"],
        )
        for tc_data in sorted(tool_call_deltas.values(), key=lambda x: list(tool_call_deltas.keys())[list(tool_call_deltas.values()).index(x)])
      ]
      # Attach to the last chunk (or the last non-usage chunk)
      for sc in reversed(chunks):
        if sc.content or sc.thoughts:
          sc.tool_calls = tool_calls
          break
      else:
        # Fallback: attach to the very last chunk
        if chunks:
          chunks[-1].tool_calls = tool_calls

    return chunks
