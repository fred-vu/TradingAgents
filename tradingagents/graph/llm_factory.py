import logging
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


def _resolve_model_alias(
    model_name: str,
    provider: str,
    provider_config: Dict[str, Any],
    logger: logging.Logger,
) -> Tuple[str, Dict[str, float] | None]:
    """Map friendly model aliases to provider-specific identifiers."""
    if provider != "openrouter":
        return model_name, None

    aliases = provider_config.get("model_aliases", {}) or {}
    resolved = aliases.get(model_name, model_name)
    if resolved != model_name:
        logger.info("OpenRouter alias '%s' mapped to '%s'", model_name, resolved)

    cost_map = provider_config.get("cost_estimates", {}) or {}
    return resolved, cost_map.get(resolved)


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

    logger = logging.getLogger("tradingagents.llm")

    deep_model, deep_cost = _resolve_model_alias(
        deep_model, provider, provider_config, logger
    )
    quick_model, quick_cost = _resolve_model_alias(
        quick_model, provider, provider_config, logger
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

    def _log_cost(model: str, cost_info: Dict[str, float] | None, role: str) -> None:
        if not cost_info:
            return
        prompt_cost = cost_info.get("prompt")
        completion_cost = cost_info.get("completion")
        logger.info(
            "Estimated OpenRouter cost for %s model '%s': prompt=%.4f, completion=%.4f (USD per 1k tokens)",
            role,
            model,
            prompt_cost or 0.0,
            completion_cost or 0.0,
        )

    _log_cost(deep_model, deep_cost, "deep-think")
    _log_cost(quick_model, quick_cost, "quick-think")

    return LLMInitResult(
        provider=provider,
        base_url=base_url,
        deep_llm=deep_llm,
        quick_llm=quick_llm,
    )
