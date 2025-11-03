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
        "model_aliases": {
            "gpt-5-mini": "openai/gpt-5-mini",
            "gpt-4o-mini": "openai/gpt-4o-mini",
            "llama3-70b": "meta-llama/llama-3.3-70b-instruct",
            "zAi-glm-4-5": "z-ai/glm-4.5-air:free",
            "deepseek-r1": "deepseek/deepseek-chat-v3-0324:free",
            "magistral-medium": "mistralai/magistral-medium-2506:thinking",
            "mistral-small": "mistralai/mistral-small-3.2-24b-instruct:free",
            "grok-4-fast": "x-ai/grok-4-fast",
            "minimax-free": "minimax/minimax-m2:free",
        },
        "cost_estimates": {
            "openai/gpt-5-mini": {"prompt": 0.25, "completion": 2.00},
            "openai/gpt-4o-mini": {"prompt": 0.15, "completion": 0.60},
            "meta-llama/llama-3.3-70b-instruct": {"prompt": 0.13, "completion": 0.38},
            "z-ai/glm-4.5-air:free": {"prompt": 0.00, "completion": 0.00},
            "mistralai/magistral-medium-2506:thinking": {
                "prompt": 2.00,
                "completion": 5.00,
            },
            "x-ai/grok-4-fast": {"prompt": 0.20, "completion": 0.50},
            "minimax/minimax-m2:free": {"prompt": 0.00, "completion": 0.00},
            "deepseek/deepseek-chat-v3-0324:free": {"prompt": 0.00, "completion": 0.00},
            "mistralai/mistral-small-3.2-24b-instruct:free": {
                "prompt": 0.00,
                "completion": 0.00,
            },
        },
        "capability_tiers": {
            "finance_safe": ["gpt-5-mini", "gpt-4o-mini", "magistral-medium"],
            "cost_saver": ["gpt-4o-mini", "magistral-medium"],
            "research_heavy": ["llama3-70b", "grok-4-fast"],
            "free_trial": [
                "zAi-glm-4-5",
                "minimax-free",
                "deepseek-r1",
                "mistral-small",
            ],
        },
        "preferred_capabilities": {
            "deep_think": "finance_safe",
            "quick_think": "cost_saver",
        },
        "blocked_models": [],
        "enable_free_models": True,
        "max_calls_per_minute": int(
            os.getenv("TRADINGAGENTS_OPENROUTER_MAX_CALLS", "20")
        ),
        ##selection mode for openrouter: cost_balanced, performance_first, balanced, or free_only
        "selection_mode": os.getenv(
            "TRADINGAGENTS_OPENROUTER_SELECTION_MODE", "balanced"
        ),
        "model_profiles": {
            "openai/gpt-5-mini": {
                "context": 200000,
                "reliability": 0.9,
                "cost_weight": 0.6,
            },
            "openai/gpt-4o-mini": {
                "context": 128000,
                "reliability": 0.95,
                "cost_weight": 0.9,
            },
            "mistralai/magistral-medium-2506:thinking": {
                "context": 32000,
                "reliability": 0.7,
                "cost_weight": 0.4,
            },
            "meta-llama/llama-3.3-70b-instruct": {
                "context": 8192,
                "reliability": 0.6,
                "cost_weight": 0.3,
            },
            "x-ai/grok-4-fast": {
                "context": 32768,
                "reliability": 0.65,
                "cost_weight": 0.35,
            },
            "z-ai/glm-4.5-air:free": {
                "context": 32000,
                "reliability": 0.7,
                "cost_weight": 1.0,
            },
            "minimax/minimax-m2:free": {
                "context": 20000,
                "reliability": 0.7,
                "cost_weight": 1.0,
            },
            "deepseek/deepseek-chat-v3-0324:free": {
                "context": 24000,
                "reliability": 0.5,
                "cost_weight": 1.0,
            },
            "mistralai/mistral-small-3.2-24b-instruct:free": {
                "context": 32000,
                "reliability": 0.45,
                "cost_weight": 1.0,
            },
        },
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


def _default_audit_dir() -> str:
    return os.getenv(
        "TRADINGAGENTS_AUDIT_LOG_DIR",
        str((_PROJECT_DIR / ".." / "audit_logs").resolve()),
    )


def _default_cache_db_path() -> str:
    return os.getenv(
        "TRADINGAGENTS_CACHE_DB",
        str((_PROJECT_DIR / ".." / "cache" / "trading_data.db").resolve()),
    )


_DEFAULT_CONFIG_TEMPLATE: Dict[str, Any] = {
    "project_dir": str(_PROJECT_DIR.resolve()),
    "results_dir": _default_results_dir(),
    "data_dir": _default_data_dir(),
    "data_cache_dir": _default_data_cache_dir(),
    "memory_dir": _default_memory_dir(),
    "log_dir": _default_log_dir(),
    "log_level": os.getenv("TRADINGAGENTS_LOG_LEVEL", "INFO"),
    "audit_log_dir": _default_audit_dir(),
    "audit_retention_days": int(os.getenv("TRADINGAGENTS_AUDIT_RETENTION", "90")),
    "cache_db_path": _default_cache_db_path(),
    "cache_ttl": {
        "get_news": int(os.getenv("TRADINGAGENTS_TTL_NEWS", "3600")),
        "get_global_news": int(os.getenv("TRADINGAGENTS_TTL_GLOBAL_NEWS", "3600")),
        "get_fundamentals": int(os.getenv("TRADINGAGENTS_TTL_FUNDAMENTALS", "86400")),
        "get_balance_sheet": int(os.getenv("TRADINGAGENTS_TTL_BALANCE_SHEET", "86400")),
        "get_cashflow": int(os.getenv("TRADINGAGENTS_TTL_CASHFLOW", "86400")),
        "get_income_statement": int(
            os.getenv("TRADINGAGENTS_TTL_INCOME_STATEMENT", "86400")
        ),
        "get_indicators": int(os.getenv("TRADINGAGENTS_TTL_INDICATORS", "900")),
        "get_stock_data": int(os.getenv("TRADINGAGENTS_TTL_STOCK_DATA", "900")),
    },
    "vendor_costs": {
        "alpha_vantage": float(os.getenv("TRADINGAGENTS_COST_ALPHA_VANTAGE", "0.0")),
        "yfinance": float(os.getenv("TRADINGAGENTS_COST_YFINANCE", "0.0")),
        "finnhub": float(os.getenv("TRADINGAGENTS_COST_FINNHUB", "0.0")),
        "openai": float(os.getenv("TRADINGAGENTS_COST_OPENAI", "0.0")),
        "openrouter": float(os.getenv("TRADINGAGENTS_COST_OPENROUTER", "0.0")),
        "google": float(os.getenv("TRADINGAGENTS_COST_GOOGLE", "0.0")),
    },
    "vendor_priority_order": os.getenv(
        "TRADINGAGENTS_VENDOR_PRIORITY_ORDER",
        "",
    ),
    "vendor_circuit_breaker_threshold": int(
        os.getenv("TRADINGAGENTS_VENDOR_CB_THRESHOLD", "3")
    ),
    "vendor_circuit_breaker_cooldown": int(
        os.getenv("TRADINGAGENTS_VENDOR_CB_COOLDOWN", "300")
    ),
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
        "core_stock_apis": "yfinance",  # Options: yfinance, alpha_vantage, local
        "technical_indicators": "yfinance",  # Options: yfinance, alpha_vantage, local
        "fundamental_data": "alpha_vantage",  # Options: openai, alpha_vantage, local
        "news_data": "alpha_vantage",  # Options: openai, alpha_vantage, google, local
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
