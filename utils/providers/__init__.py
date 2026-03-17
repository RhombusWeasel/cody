from utils.providers.base import BaseProvider, ChatResponse
from utils.providers.ollama import OllamaProvider
from utils.providers.openai import OpenAIProvider
from utils.cfg_man import cfg

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
