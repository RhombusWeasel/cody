from ollama import Client
from utils.providers.base import ChatResponse, Message, ToolCall


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
    kwargs = {"model": model, "messages": messages, "options": options}
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
