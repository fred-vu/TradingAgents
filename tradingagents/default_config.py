import os
from copy import deepcopy
from pathlib import Path
from typing import Dict, Any

_PROJECT_DIR = Path(__file__).resolve().parent


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


_DEFAULT_PROVIDER_CONFIG: Dict[str, Dict[str, Any]] = {
    "openai": {
        "api_key_env": "OPENAI_API_KEY",
        "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        "require_api_key": True,
    },
    "openrouter": {
        "api_key_env": "OPENROUTER_API_KEY",
        "base_url": os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        "require_api_key": True,
    },
    "ollama": {
        "api_key_env": os.getenv("OLLAMA_API_KEY_ENV") or None,
        "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
        "require_api_key": False,
    },
    "anthropic": {
        "api_key_env": "ANTHROPIC_API_KEY",
        "require_api_key": True,
    },
    "google": {
        "api_key_env": "GOOGLE_API_KEY",
        "require_api_key": True,
    },
}


def _default_results_dir() -> str:
    return os.getenv(
        "TRADINGAGENTS_RESULTS_DIR",
        str((_PROJECT_DIR / ".." / "results").resolve()),
    )


def _default_data_dir() -> str:
    return os.getenv(
        "TRADINGAGENTS_DATA_DIR",
        str((_PROJECT_DIR / "dataflows" / "data_cache").resolve()),
    )


def _default_data_cache_dir() -> str:
    return os.getenv(
        "TRADINGAGENTS_DATA_CACHE_DIR",
        str((_PROJECT_DIR / "dataflows" / "data_cache").resolve()),
    )


def _default_memory_dir() -> str:
    return os.getenv(
        "TRADINGAGENTS_MEMORY_DIR",
        str((_PROJECT_DIR / ".." / "memory").resolve()),
    )


def _default_log_dir() -> str:
    return os.getenv(
        "TRADINGAGENTS_LOG_DIR",
        str((_PROJECT_DIR / ".." / "logs").resolve()),
    )


_DEFAULT_CONFIG_TEMPLATE: Dict[str, Any] = {
    "project_dir": str(_PROJECT_DIR.resolve()),
    "results_dir": _default_results_dir(),
    "data_dir": _default_data_dir(),
    "data_cache_dir": _default_data_cache_dir(),
    "memory_dir": _default_memory_dir(),
    "log_dir": _default_log_dir(),
    "log_level": os.getenv("TRADINGAGENTS_LOG_LEVEL", "INFO"),
    # LLM settings
    "llm_provider": "openai",
    "deep_think_llm": "o4-mini",
    "quick_think_llm": "gpt-4o-mini",
    "backend_url": _DEFAULT_PROVIDER_CONFIG["openai"]["base_url"],
    # LangSmith / observability
    "enable_langsmith": _bool_env("TRADINGAGENTS_ENABLE_LANGSMITH", False),
    "langsmith_project": os.getenv("LANGSMITH_PROJECT", "TradingAgents"),
    "langsmith_api_key": os.getenv("LANGSMITH_API_KEY", ""),
    # Debate and discussion settings
    "max_debate_rounds": 1,
    "max_risk_discuss_rounds": 1,
    "max_recur_limit": 100,
    # Audit logging
    "audit_log_filename": "trade_audit.jsonl",
    # Data vendor configuration
    "data_vendors": {
        "core_stock_apis": "yfinance",        # Options: yfinance, alpha_vantage, local
        "technical_indicators": "yfinance",   # Options: yfinance, alpha_vantage, local
        "fundamental_data": "alpha_vantage",  # Options: openai, alpha_vantage, local
        "news_data": "alpha_vantage",         # Options: openai, alpha_vantage, google, local
    },
    "tool_vendors": {},
    "provider_config": deepcopy(_DEFAULT_PROVIDER_CONFIG),
}


def build_default_config() -> Dict[str, Any]:
    """Return a fresh default configuration dictionary."""
    config = deepcopy(_DEFAULT_CONFIG_TEMPLATE)
    config["provider_config"] = deepcopy(_DEFAULT_PROVIDER_CONFIG)
    return config


def copy_default_config() -> Dict[str, Any]:
    """External helper for callers needing an isolated default config."""
    return build_default_config()


def merge_provider_config(
    base_config: Dict[str, Dict[str, Any]],
    overrides: Dict[str, Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """Merge provider override dictionaries into the base provider config."""
    merged = deepcopy(base_config)
    for provider, settings in overrides.items():
        if provider in merged and isinstance(merged[provider], dict):
            merged[provider].update(settings)
        else:
            merged[provider] = settings
    return merged


DEFAULT_CONFIG = build_default_config()
