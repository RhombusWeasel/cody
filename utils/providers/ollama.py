import json

from ollama import Client
from utils.cfg_man import cfg
from utils.providers.base import ChatResponse, Message, StreamChunk, ToolCall as ProviderToolCall, TokenUsage
from utils.providers.ollama_vault import resolve_ollama_api_key


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
    # Lazy initialization - don't create client until needed
    # This allows resolve_ollama_api_key() to work after vault unlock
    self._client = None
    self._host_cache = None
    self._api_key_cache = None
  
  def _get_client(self):
    """Get or create the Ollama client, resolving API key if needed."""
    # Check if we need to re-resolve the API key (vault may have been unlocked)
    raw = cfg.get("providers.ollama.base_url") or ""
    host = raw.strip() if isinstance(raw, str) else str(raw)
    if not host:
      host = "http://127.0.0.1:11434"
    
    api_key = resolve_ollama_api_key()
    
    # If client exists and nothing changed, reuse it
    if self._client is not None:
      if self._host_cache == host and self._api_key_cache == api_key:
        return self._client
      # Something changed (vault unlocked, key changed), recreate client
      self._client = None
    
    # Create new client
    if api_key:
      self._client = Client(
        host=host,
        headers={"Authorization": f"Bearer {api_key}"},
      )
    else:
      self._client = Client(host=host)
    
    self._host_cache = host
    self._api_key_cache = api_key
    return self._client

  def chat(
    self,
    model: str,
    messages: list[dict],
    tools: list | None = None,
    options: dict | None = None,
  ) -> ChatResponse:
    client = self._get_client()  # Lazy init here, after vault unlock
    kwargs = {
      "model": model,
      "messages": _messages_for_ollama_client(messages),
      "options": options,
    }
    if tools:
      kwargs["tools"] = tools
    resp = client.chat(**kwargs)
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
    usage = None
    prompt_tokens = getattr(resp, "prompt_eval_count", None)
    completion_tokens = getattr(resp, "eval_count", None)
    if prompt_tokens is not None or completion_tokens is not None:
      pt = prompt_tokens or 0
      ct = completion_tokens or 0
      context_window = (options or {}).get("num_ctx", 0) or 0
      usage = TokenUsage(
        prompt_tokens=pt,
        completion_tokens=ct,
        total_tokens=pt + ct,
        context_window=context_window,
      )
    return ChatResponse(
      message=Message(
        content=resp.message.content or "",
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
    """Stream a chat response, capturing thoughts/reasoning content."""
    client = self._get_client()
    kwargs = {
      "model": model,
      "messages": _messages_for_ollama_client(messages),
      "options": options,
      "stream": True,
    }
    if tools:
      kwargs["tools"] = tools

    chunks: list[StreamChunk] = []
    for chunk in client.chat(**kwargs):
      content = chunk.message.content or ""
      thoughts = None

      # Ollama may include reasoning in the response
      # Check for 'reasoning' field if present in the chunk
      if hasattr(chunk.message, "reasoning") and chunk.message.reasoning:
        thoughts = chunk.message.reasoning

      sc = StreamChunk(
        content=content,
        thoughts=thoughts,
        done=chunk.done if hasattr(chunk, "done") else False,
      )
      if chunk.done:
        prompt_tokens = getattr(chunk, "prompt_eval_count", None)
        completion_tokens = getattr(chunk, "eval_count", None)
        if prompt_tokens is not None or completion_tokens is not None:
          pt = prompt_tokens or 0
          ct = completion_tokens or 0
          context_window = (options or {}).get("num_ctx", 0) or 0
          sc.usage = TokenUsage(
            prompt_tokens=pt,
            completion_tokens=ct,
            total_tokens=pt + ct,
            context_window=context_window,
          )
      chunks.append(sc)
    return chunks