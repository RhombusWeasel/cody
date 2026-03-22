from utils.providers.base import BaseProvider, ChatResponse
from utils.providers.ollama import OllamaProvider
from utils.providers.openai import OpenAIProvider
from utils.cfg_man import cfg, register_default_config

register_default_config({
  "session": {"provider": "ollama"},
  "providers": {
    "ollama": {
      "base_url": "http://127.0.0.1:11434",
      "model": "qwen3-coder:30b",
      "opts": {
        "num_ctx": 16384,
        "temperature": 0.3,
        "seed": 42,
        "top_k": 30,
        "top_p": 0.5,
      },
    },
    "openai": {
      "model": "gpt-5.4-mini",
      "opts": {"temperature": 0.3},
    },
  },
})

PROVIDERS: dict[str, type] = {
  "ollama": OllamaProvider,
  "openai": OpenAIProvider,
}


def get_provider() -> BaseProvider:
  name = (cfg.get("session.provider", "ollama") or "").lower()
  cls = PROVIDERS.get(name, OllamaProvider)
  return cls()


def get_provider_config() -> tuple[str, str, dict]:
  """Return (provider_name, model, opts) for the active provider."""
  name = (cfg.get("session.provider", "ollama") or "").lower()
  model = cfg.get(f"providers.{name}.model", "")
  opts = cfg.get(f"providers.{name}.opts") or {}
  return name, model, opts
