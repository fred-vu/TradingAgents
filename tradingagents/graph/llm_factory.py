import os
from dataclasses import dataclass
from typing import Any, Dict, Tuple

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI


class LLMConfigurationError(RuntimeError):
    """Raised when provider configuration is invalid or incomplete."""


@dataclass
class LLMInitResult:
    provider: str
    base_url: str | None
    deep_llm: Any
    quick_llm: Any


def _resolve_provider_settings(config: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    provider = (config.get("llm_provider") or "openai").lower()
    provider_config = (config.get("provider_config") or {}).get(provider)
    if not provider_config:
        raise LLMConfigurationError(
            f"Unsupported or undefined LLM provider '{provider}'. "
            "Update 'provider_config' with the necessary settings."
        )
    return provider, provider_config


def _resolve_api_key(
    provider: str,
    provider_config: Dict[str, Any],
    global_config: Dict[str, Any],
) -> str | None:
    api_key_overrides = (global_config.get("api_keys") or {}).get(provider)
    if api_key_overrides:
        return api_key_overrides

    api_key = provider_config.get("api_key")
    api_key_env = provider_config.get("api_key_env")
    if not api_key and api_key_env:
        api_key = os.getenv(api_key_env)

    requires_key = provider_config.get("require_api_key", True)
    if requires_key and not api_key:
        suffix = (
            f" Set the '{api_key_env}' environment variable or provide an API key via config."
            if api_key_env
            else " Provide an API key via config."
        )
        raise LLMConfigurationError(
            f"API key missing for provider '{provider}'.{suffix}"
        )
    return api_key


def build_llms(config: Dict[str, Any]) -> LLMInitResult:
    """Instantiate provider-specific LLM clients for deep/quick thinking roles."""
    provider, provider_config = _resolve_provider_settings(config)
    api_key = _resolve_api_key(provider, provider_config, config)
    base_url = provider_config.get("base_url")

    deep_model = config.get("deep_think_llm")
    quick_model = config.get("quick_think_llm")
    if not deep_model or not quick_model:
        raise LLMConfigurationError(
            "Both 'deep_think_llm' and 'quick_think_llm' must be configured."
        )

    if provider in {"openai", "openrouter", "ollama"}:
        kwargs: Dict[str, Any] = {}
        if api_key:
            kwargs["api_key"] = api_key
        if base_url:
            kwargs["base_url"] = base_url
        deep_llm = ChatOpenAI(model=deep_model, **kwargs)
        quick_llm = ChatOpenAI(model=quick_model, **kwargs)
    elif provider == "anthropic":
        kwargs = {}
        if api_key:
            kwargs["api_key"] = api_key
        deep_llm = ChatAnthropic(model=deep_model, **kwargs)
        quick_llm = ChatAnthropic(model=quick_model, **kwargs)
    elif provider == "google":
        kwargs = {}
        if api_key:
            kwargs["google_api_key"] = api_key
        deep_llm = ChatGoogleGenerativeAI(model=deep_model, **kwargs)
        quick_llm = ChatGoogleGenerativeAI(model=quick_model, **kwargs)
    else:
        raise LLMConfigurationError(f"Unsupported LLM provider '{provider}'.")

    return LLMInitResult(
        provider=provider,
        base_url=base_url,
        deep_llm=deep_llm,
        quick_llm=quick_llm,
    )
