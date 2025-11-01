import logging
import time
from typing import Annotated

logger = logging.getLogger("tradingagents.dataflows")

# Import from vendor-specific modules
from .local import get_YFin_data, get_finnhub_news, get_finnhub_company_insider_sentiment, get_finnhub_company_insider_transactions, get_simfin_balance_sheet, get_simfin_cashflow, get_simfin_income_statements, get_reddit_global_news, get_reddit_company_news

try:
    from .y_finance import (
        get_YFin_data_online,
        get_stock_stats_indicators_window,
        get_balance_sheet as get_yfinance_balance_sheet,
        get_cashflow as get_yfinance_cashflow,
        get_income_statement as get_yfinance_income_statement,
        get_insider_transactions as get_yfinance_insider_transactions,
    )
    YFINANCE_AVAILABLE = True
except ModuleNotFoundError:
    logger.warning("yfinance not installed; yfinance vendor functionality disabled")
    YFINANCE_AVAILABLE = False

    def _missing(*args, **kwargs):
        raise ModuleNotFoundError("yfinance is required for this vendor but is not installed.")

    get_YFin_data_online = _missing
    get_stock_stats_indicators_window = _missing
    get_yfinance_balance_sheet = _missing
    get_yfinance_cashflow = _missing
    get_yfinance_income_statement = _missing
    get_yfinance_insider_transactions = _missing

try:
    from .google import get_google_news
    GOOGLE_NEWS_AVAILABLE = True
except ModuleNotFoundError:
    logger.warning("Google News dependencies missing; google vendor functionality disabled")
    GOOGLE_NEWS_AVAILABLE = False

    def get_google_news(*args, **kwargs):
        raise ModuleNotFoundError("Google News dependencies (tenacity, bs4, requests) are required")
from .openai import get_stock_news_openai, get_global_news_openai, get_fundamentals_openai
from .alpha_vantage import (
    get_stock as get_alpha_vantage_stock,
    get_indicator as get_alpha_vantage_indicator,
    get_fundamentals as get_alpha_vantage_fundamentals,
    get_balance_sheet as get_alpha_vantage_balance_sheet,
    get_cashflow as get_alpha_vantage_cashflow,
    get_income_statement as get_alpha_vantage_income_statement,
    get_insider_transactions as get_alpha_vantage_insider_transactions,
    get_news as get_alpha_vantage_news
)
from .alpha_vantage_common import AlphaVantageRateLimitError
from .finnhub_api import (
    get_finnhub_company_news,
    get_finnhub_basic_financials,
    get_finnhub_income_statement,
    get_finnhub_balance_sheet,
    get_finnhub_cashflow,
    IS_AVAILABLE as FINNHUB_AVAILABLE,
)
from .newsapi_client import (
    get_newsapi_company_news,
    get_newsapi_global_news,
    IS_AVAILABLE as NEWSAPI_AVAILABLE,
)

# Configuration and routing logic
from .config import get_config
from .cache import get_cache, ResponseCache

# Tools organized by category
TOOLS_CATEGORIES = {
    "core_stock_apis": {
        "description": "OHLCV stock price data",
        "tools": [
            "get_stock_data"
        ]
    },
    "technical_indicators": {
        "description": "Technical analysis indicators",
        "tools": [
            "get_indicators"
        ]
    },
    "fundamental_data": {
        "description": "Company fundamentals",
        "tools": [
            "get_fundamentals",
            "get_balance_sheet",
            "get_cashflow",
            "get_income_statement"
        ]
    },
    "news_data": {
        "description": "News (public/insiders, original/processed)",
        "tools": [
            "get_news",
            "get_global_news",
            "get_insider_sentiment",
            "get_insider_transactions",
        ]
    }
}

_vendor_failure_counts: dict[str, int] = {}
_vendor_circuit_breaker: dict[str, float] = {}


def _reset_vendor_state():
    _vendor_failure_counts.clear()
    _vendor_circuit_breaker.clear()


def reset_vendor_state_for_tests():
    _reset_vendor_state()


def _is_vendor_available(vendor: str) -> bool:
    return VENDOR_AVAILABILITY.get(vendor, True)


def _register_vendor_failure(vendor: str, config) -> None:
    threshold = int(config.get("vendor_circuit_breaker_threshold", 3) or 3)
    cooldown = int(config.get("vendor_circuit_breaker_cooldown", 300) or 300)
    count = _vendor_failure_counts.get(vendor, 0) + 1
    _vendor_failure_counts[vendor] = count
    if count >= threshold:
        unblock_time = time.time() + cooldown
        _vendor_circuit_breaker[vendor] = unblock_time
        _vendor_failure_counts[vendor] = 0
        logger.warning(
            "Circuit breaker tripped for vendor '%s' after %d consecutive failures; skipping for %ss",
            vendor,
            threshold,
            cooldown,
        )


def _clear_vendor_failure(vendor: str) -> None:
    _vendor_failure_counts.pop(vendor, None)
    _vendor_circuit_breaker.pop(vendor, None)

VENDOR_LIST = [
    "local",
    "yfinance",
    "openai",
    "google",
    "finnhub",
    "newsapi",
]

VENDOR_AVAILABILITY = {
    "local": True,
    "yfinance": YFINANCE_AVAILABLE,
    "openai": True,
    "google": GOOGLE_NEWS_AVAILABLE,
    "finnhub": FINNHUB_AVAILABLE,
    "newsapi": NEWSAPI_AVAILABLE,
}

# Mapping of methods to their vendor-specific implementations
VENDOR_METHODS = {
    # core_stock_apis
    "get_stock_data": {
        "alpha_vantage": get_alpha_vantage_stock,
        "yfinance": get_YFin_data_online,
        "local": get_YFin_data,
    },
    # technical_indicators
    "get_indicators": {
        "alpha_vantage": get_alpha_vantage_indicator,
        "yfinance": get_stock_stats_indicators_window,
        "local": get_stock_stats_indicators_window
    },
    # fundamental_data
    "get_fundamentals": {
        "alpha_vantage": get_alpha_vantage_fundamentals,
        "openai": get_fundamentals_openai,
        "finnhub": get_finnhub_basic_financials,
    },
    "get_balance_sheet": {
        "alpha_vantage": get_alpha_vantage_balance_sheet,
        "yfinance": get_yfinance_balance_sheet,
        "local": get_simfin_balance_sheet,
        "finnhub": get_finnhub_balance_sheet,
    },
    "get_cashflow": {
        "alpha_vantage": get_alpha_vantage_cashflow,
        "yfinance": get_yfinance_cashflow,
        "local": get_simfin_cashflow,
        "finnhub": get_finnhub_cashflow,
    },
    "get_income_statement": {
        "alpha_vantage": get_alpha_vantage_income_statement,
        "yfinance": get_yfinance_income_statement,
        "local": get_simfin_income_statements,
        "finnhub": get_finnhub_income_statement,
    },
    # news_data
    "get_news": {
        "alpha_vantage": get_alpha_vantage_news,
        "openai": get_stock_news_openai,
        "google": get_google_news,
        "finnhub": get_finnhub_company_news,
        "newsapi": get_newsapi_company_news,
        "local": [get_finnhub_news, get_reddit_company_news, get_google_news],
    },
    "get_global_news": {
        "openai": get_global_news_openai,
        "newsapi": get_newsapi_global_news,
        "local": get_reddit_global_news
    },
    "get_insider_sentiment": {
        "local": get_finnhub_company_insider_sentiment
    },
    "get_insider_transactions": {
        "alpha_vantage": get_alpha_vantage_insider_transactions,
        "yfinance": get_yfinance_insider_transactions,
        "local": get_finnhub_company_insider_transactions,
    },
}

def get_category_for_method(method: str) -> str:
    """Get the category that contains the specified method."""
    for category, info in TOOLS_CATEGORIES.items():
        if method in info["tools"]:
            return category
    raise ValueError(f"Method '{method}' not found in any category")

def get_vendor(category: str, method: str = None) -> str:
    """Get the configured vendor for a data category or specific tool method.
    Tool-level configuration takes precedence over category-level.
    """
    config = get_config()

    # Check tool-level configuration first (if method provided)
    if method:
        tool_vendors = config.get("tool_vendors", {})
        if method in tool_vendors:
            return tool_vendors[method]

    # Fall back to category-level configuration
    return config.get("data_vendors", {}).get(category, "default")

def route_to_vendor(method: str, *args, **kwargs):
    """Route method calls to appropriate vendor implementation with fallback support."""
    config = get_config()
    cache = get_cache()
    ttl_map = config.get("cache_ttl", {})
    ttl_seconds = ttl_map.get(method, 0)
    cache_key = None

    if cache and ttl_seconds:
        cache_key = ResponseCache.make_key(method, args, kwargs)
        cached_response = cache.get(method, cache_key, ttl_seconds)
        if cached_response is not None:
            logger.debug("Cache hit for method '%s'", method)
            return cached_response

    category = get_category_for_method(method)
    vendor_config = get_vendor(category, method)

    # Handle comma-separated vendors
    primary_vendors = [v.strip() for v in vendor_config.split(',')]

    if method not in VENDOR_METHODS:
        raise ValueError(f"Method '{method}' not supported")

    # Get all available vendors for this method for fallback
    all_available_vendors = list(VENDOR_METHODS[method].keys())
    
    # Create fallback vendor list: primary vendors first, then remaining vendors as fallbacks
    fallback_vendors = primary_vendors.copy()
    for vendor in all_available_vendors:
        if vendor not in fallback_vendors:
            fallback_vendors.append(vendor)

    priority_spec = config.get("vendor_priority_order") or ""
    if priority_spec:
        priority_list = [v.strip() for v in priority_spec.split(",") if v.strip()]
        if priority_list:
            fallback_vendors = sorted(
                fallback_vendors,
                key=lambda v: priority_list.index(v) if v in priority_list else len(priority_list),
            )

    # Debug: Print fallback ordering
    primary_str = " → ".join(primary_vendors)
    fallback_str = " → ".join(fallback_vendors)
    logger.debug(
        "%s - Primary: [%s] | Full fallback order: [%s]",
        method,
        primary_str,
        fallback_str,
    )

    # Track results and execution state
    results = []
    vendor_attempt_count = 0
    any_primary_vendor_attempted = False
    successful_vendor = None

    for vendor in fallback_vendors:
        if vendor not in VENDOR_METHODS[method]:
            if vendor in primary_vendors:
                logger.info(
                    "Vendor '%s' not supported for method '%s', falling back to next vendor",
                    vendor,
                    method,
                )
            continue

        if not _is_vendor_available(vendor):
            logger.info(
                "Vendor '%s' unavailable in current environment, skipping",
                vendor,
            )
            continue

        breaker_until = _vendor_circuit_breaker.get(vendor)
        if breaker_until and time.time() < breaker_until:
            logger.warning(
                "Vendor '%s' skipped due to circuit breaker until %.0f",
                vendor,
                breaker_until,
            )
            continue

        vendor_impl = VENDOR_METHODS[method][vendor]
        is_primary_vendor = vendor in primary_vendors
        vendor_attempt_count += 1

        # Track if we attempted any primary vendor
        if is_primary_vendor:
            any_primary_vendor_attempted = True

        # Debug: Print current attempt
        vendor_type = "PRIMARY" if is_primary_vendor else "FALLBACK"
        logger.debug(
            "Attempting %s vendor '%s' for %s (attempt #%d)",
            vendor_type,
            vendor,
            method,
            vendor_attempt_count,
        )

        # Handle list of methods for a vendor
        if isinstance(vendor_impl, list):
            vendor_methods = [(impl, vendor) for impl in vendor_impl]
            logger.debug(
                "Vendor '%s' has multiple implementations: %d functions",
                vendor,
                len(vendor_methods),
            )
        else:
            vendor_methods = [(vendor_impl, vendor)]

        # Run methods for this vendor
        vendor_results = []
        for impl_func, vendor_name in vendor_methods:
            try:
                logger.debug(
                    "Calling %s from vendor '%s'", impl_func.__name__, vendor_name
                )
                result = impl_func(*args, **kwargs)
                vendor_results.append(result)
                logger.debug(
                    "%s from vendor '%s' completed successfully",
                    impl_func.__name__,
                    vendor_name,
                )
                    
            except AlphaVantageRateLimitError as e:
                if vendor == "alpha_vantage":
                    logger.warning(
                        "Alpha Vantage rate limit exceeded, falling back to next available vendor"
                    )
                    logger.debug("Rate limit details: %s", e)
                # Continue to next vendor for fallback
                continue
            except Exception as e:
                # Log error but continue with other implementations
                logger.warning(
                    "%s from vendor '%s' failed: %s",
                    impl_func.__name__,
                    vendor_name,
                    e,
                )
                continue

        # Add this vendor's results
        if vendor_results:
            results.extend(vendor_results)
            successful_vendor = vendor
            result_summary = f"Got {len(vendor_results)} result(s)"
            logger.debug(
                "Vendor '%s' succeeded - %s", vendor, result_summary
            )
            _clear_vendor_failure(vendor)

            # Stopping logic: Stop after first successful vendor for single-vendor configs
            # Multiple vendor configs (comma-separated) may want to collect from multiple sources
            if len(primary_vendors) == 1:
                logger.debug(
                    "Stopping after successful vendor '%s' (single-vendor config)",
                    vendor,
                )
                break
        else:
            logger.warning("Vendor '%s' produced no results", vendor)
            _register_vendor_failure(vendor, config)

    # Final result summary
    if not results:
        logger.error(
            "All %d vendor attempts failed for method '%s'",
            vendor_attempt_count,
            method,
        )
        if cache and cache_key:
            stale = cache.get_stale(method, cache_key)
            if stale is not None:
                logger.warning(
                    "Returning stale cached data for method '%s' after vendor failures",
                    method,
                )
                return stale
        raise RuntimeError(f"All vendor implementations failed for method '{method}'")

    logger.debug(
        "Method '%s' completed with %d result(s) from %d vendor attempt(s)",
        method,
        len(results),
        vendor_attempt_count,
    )

    if len(results) == 1:
        final_response = results[0]
    else:
        final_response = '\n'.join(str(result) for result in results)

    if cache and ttl_seconds and cache_key and successful_vendor:
        cache.set(method, cache_key, final_response, successful_vendor)
        logger.debug(
            "Cached response for method '%s' via vendor '%s' (ttl=%ss)",
            method,
            successful_vendor,
            ttl_seconds,
        )

    vendor_costs = config.get("vendor_costs", {})
    cost = vendor_costs.get(successful_vendor)
    if cost:
        logger.info(
            "Vendor '%s' cost estimated at %.4f credits for method '%s'",
            successful_vendor,
            cost,
            method,
        )
    else:
        logger.debug(
            "Vendor '%s' completed method '%s' without cost estimate",
            successful_vendor,
            method,
        )

    return final_response
