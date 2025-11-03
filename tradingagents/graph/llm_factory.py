import asyncio
import logging
import os
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Deque, Dict, Iterable, List, Sequence, Tuple

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.runnables import Runnable

from tradingagents.logging_utils import emit_audit_record

try:  # pragma: no cover - optional dependency in tests
    from openai import BadRequestError, RateLimitError
except Exception:  # pragma: no cover
    BadRequestError = RateLimitError = None


class LLMConfigurationError(RuntimeError):
    """Raised when provider configuration is invalid or incomplete."""


@dataclass
class LLMInitResult:
    provider: str
    base_url: str | None
    deep_llm: Any
    quick_llm: Any


@dataclass
class ModelCandidate:
    alias: str
    resolved: str
    cost: Dict[str, float] | None
    score: float
    tier: str | None


_RATE_LIMIT_STATE: Dict[str, Deque[float]] = defaultdict(deque)


class _FallbackExecutor:
    """Shared fallback execution helper for chat models and bound tool runnables."""

    RATE_LIMIT_MAX_RETRIES = 2
    RATE_LIMIT_BASE_BACKOFF = 0.75
    RATE_LIMIT_MAX_BACKOFF = 8.0

    def __init__(
        self,
        name: str,
        candidates: Sequence[ModelCandidate],
        executors: Sequence[Any],
        logger: logging.Logger,
        rate_limit_key: str | None = None,
        max_calls_per_minute: int | None = None,
    ) -> None:
        if len(candidates) != len(executors):
            raise ValueError("Candidates and executors length mismatch.")
        self._name = name
        self._candidates = list(candidates)
        self._executors = list(executors)
        self._logger = logger
        self._rate_limit_key = rate_limit_key
        self._max_calls_per_minute = max_calls_per_minute if max_calls_per_minute and max_calls_per_minute > 0 else None

    def _classify_exception(self, exc: Exception) -> str:
        if RateLimitError and isinstance(exc, RateLimitError):
            return "rate_limit"
        if hasattr(exc, "status_code") and getattr(exc, "status_code") == 429:
            return "rate_limit"
        if BadRequestError and isinstance(exc, BadRequestError):
            return "bad_request"
        return "error"

    def _emit_fallback_event(
        self,
        candidate: ModelCandidate,
        exc: Exception,
        attempt: int,
        stage: str,
        next_candidate: ModelCandidate | None,
    ) -> None:
        record = {
            "event": "llm_fallback",
            "provider": "openrouter",
            "role": self._name,
            "stage": stage,
            "attempt": attempt,
            "failed_model_alias": candidate.alias,
            "failed_model_resolved": candidate.resolved,
            "failed_model_tier": getattr(candidate, "tier", None),
            "error": repr(exc),
        }
        if next_candidate:
            record["next_model_alias"] = next_candidate.alias
            record["next_model_resolved"] = next_candidate.resolved
        try:
            emit_audit_record(record)
        except Exception:  # pragma: no cover - audit logging should not break flow
            self._logger.debug("Failed to emit audit record for fallback", exc_info=True)

    def _enforce_rate_limit(self) -> None:
        if not self._rate_limit_key or not self._max_calls_per_minute:
            return
        timestamps = _RATE_LIMIT_STATE[self._rate_limit_key]
        now = time.time()
        window_start = now - 60.0
        while timestamps and timestamps[0] < window_start:
            timestamps.popleft()
        if len(timestamps) >= self._max_calls_per_minute:
            sleep_for = max(0.0, 60.0 - (now - timestamps[0]))
            if sleep_for > 0:
                self._logger.debug(
                    "Rate limit reached for %s (limit %d/min); sleeping %.2fs",
                    self._rate_limit_key,
                    self._max_calls_per_minute,
                    sleep_for,
                )
                time.sleep(sleep_for)
            now = time.time()
            window_start = now - 60.0
            while timestamps and timestamps[0] < window_start:
                timestamps.popleft()
        timestamps.append(time.time())

    def _run_sync(self, method_name: str, *args: Any, **kwargs: Any) -> Any:
        last_exc: Exception | None = None
        for idx, executor in enumerate(self._executors):
            candidate = self._candidates[idx]
            attempt = 0
            while True:
                attempt += 1
                try:
                    self._enforce_rate_limit()
                    method = getattr(executor, method_name)
                    result = method(*args, **kwargs)
                    if attempt > 1 or idx > 0:
                        self._logger.info(
                            "OpenRouter fallback succeeded for '%s' using model '%s'",
                            self._name,
                            candidate.resolved,
                        )
                    return result
                except Exception as exc:  # pragma: no cover - relies on runtime behavior
                    last_exc = exc
                    classification = self._classify_exception(exc)
                    next_candidate = (
                        self._candidates[idx + 1]
                        if idx + 1 < len(self._candidates)
                        else None
                    )
                    self._logger.warning(
                        "Model '%s' failed during '%s' (%s): %s",
                        candidate.resolved,
                        self._name,
                        classification,
                        exc,
                    )
                    self._emit_fallback_event(
                        candidate, exc, attempt, method_name, next_candidate
                    )

                    if (
                        classification == "rate_limit"
                        and attempt <= self.RATE_LIMIT_MAX_RETRIES
                    ):
                        wait = min(
                            self.RATE_LIMIT_BASE_BACKOFF * (2 ** (attempt - 1)),
                            self.RATE_LIMIT_MAX_BACKOFF,
                        )
                        self._logger.info(
                            "Retrying model '%s' after %.2fs backoff "
                            "(attempt %d for '%s')",
                            candidate.resolved,
                            wait,
                            attempt,
                            self._name,
                        )
                        time.sleep(wait)
                        continue

                    # Break out and try the next candidate.
                    break
        if last_exc:
            raise last_exc
        raise LLMConfigurationError("No OpenRouter models available for fallback.")

    async def _run_async(self, method_name: str, *args: Any, **kwargs: Any) -> Any:
        return await asyncio.to_thread(self._run_sync, method_name, *args, **kwargs)


class _FallbackRunnable(Runnable):
    """Runnable wrapper around tool-bound runnables with fallback behavior."""

    def __init__(
        self,
        name: str,
        candidates: Sequence[ModelCandidate],
        runnables: Sequence[Any],
        logger: logging.Logger,
        rate_limit_key: str | None = None,
        max_calls_per_minute: int | None = None,
    ) -> None:
        super().__init__()
        self._executor = _FallbackExecutor(
            name,
            candidates,
            runnables,
            logger,
            rate_limit_key,
            max_calls_per_minute,
        )
        self._primary = runnables[0]

    def invoke(self, input: Any, config: Dict[str, Any] | None = None, **kwargs: Any) -> Any:
        return self._executor._run_sync("invoke", input, config=config, **kwargs)

    async def ainvoke(
        self,
        input: Any,
        config: Dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        return await self._executor._run_async("invoke", input, config=config, **kwargs)

    def batch(
        self,
        inputs: Sequence[Any],
        config: Dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        return self._executor._run_sync("batch", inputs, config=config, **kwargs)

    async def abatch(
        self,
        inputs: Sequence[Any],
        config: Dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        return await self._executor._run_async("batch", inputs, config=config, **kwargs)

    def stream(
        self,
        input: Any,
        config: Dict[str, Any] | None = None,
        **kwargs: Any,
    ):
        return self._executor._run_sync("stream", input, config=config, **kwargs)

    async def astream(
        self,
        input: Any,
        config: Dict[str, Any] | None = None,
        **kwargs: Any,
    ):
        return await self._executor._run_async("astream", input, config=config, **kwargs)

    def __getattr__(self, item: str) -> Any:  # pragma: no cover - passthrough
        return getattr(self._primary, item)


class FallbackChatModel:
    """Wrapper around multiple ChatOpenAI clients with fallback + retry semantics."""

    def __init__(
        self,
        name: str,
        candidates: Sequence[ModelCandidate],
        chat_models: Sequence[ChatOpenAI],
        logger: logging.Logger,
        rate_limit_key: str | None = None,
        max_calls_per_minute: int | None = None,
    ) -> None:
        self._executor = _FallbackExecutor(
            name,
            candidates,
            chat_models,
            logger,
            rate_limit_key,
            max_calls_per_minute,
        )
        self._candidates = list(candidates)
        self._chat_models = list(chat_models)
        self._primary = chat_models[0]
        self._name = name
        self._logger = logger
        self._rate_limit_key = rate_limit_key
        self._max_calls_per_minute = max_calls_per_minute

    def invoke(self, *args: Any, **kwargs: Any) -> Any:
        return self._executor._run_sync("invoke", *args, **kwargs)

    async def ainvoke(self, *args: Any, **kwargs: Any) -> Any:
        return await self._executor._run_async("invoke", *args, **kwargs)

    def batch(self, *args: Any, **kwargs: Any) -> Any:
        return self._executor._run_sync("batch", *args, **kwargs)

    async def abatch(self, *args: Any, **kwargs: Any) -> Any:
        return await self._executor._run_async("batch", *args, **kwargs)

    def bind_tools(self, tools: Iterable[Any], **kwargs: Any) -> _FallbackRunnable:
        tool_list = list(tools)
        rate_limit_key = kwargs.pop("rate_limit_key", None) or self._rate_limit_key
        max_calls_per_minute = kwargs.pop("max_calls_per_minute", None)
        if max_calls_per_minute is None:
            max_calls_per_minute = self._max_calls_per_minute
        bound = [model.bind_tools(tool_list, **kwargs) for model in self._chat_models]
        return _FallbackRunnable(
            f"{self._name}.tools",
            self._candidates,
            bound,
            self._logger,
            rate_limit_key,
            max_calls_per_minute,
        )

    @property
    def primary_model(self) -> str:
        return self._candidates[0].resolved

    @property
    def model_name(self) -> str:
        return self.primary_model

    def __getattr__(self, item: str) -> Any:  # pragma: no cover - passthrough
        return getattr(self._primary, item)


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


def _ensure_sequence(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value]
    return [str(value)]


def _alias_tier_map(provider_config: Dict[str, Any]) -> Dict[str, str]:
    capability_tiers = provider_config.get("capability_tiers", {}) or {}
    mapping: Dict[str, str] = {}
    for tier, aliases in capability_tiers.items():
        for alias in aliases:
            mapping[str(alias)] = tier
    return mapping


def _collect_alias_candidates(
    role: str,
    requested: Sequence[str],
    provider_config: Dict[str, Any],
    logger: logging.Logger,
) -> List[Tuple[str, str | None]]:
    capability_tiers = provider_config.get("capability_tiers", {}) or {}
    preferred_capabilities = provider_config.get("preferred_capabilities", {}) or {}
    blocked = {str(m).lower() for m in provider_config.get("blocked_models", [])}
    enable_free = bool(provider_config.get("enable_free_models", False))
    selection_mode = str(provider_config.get("selection_mode", "balanced")).lower()
    free_only = selection_mode == "free_only"
    alias_to_tier = _alias_tier_map(provider_config)
    model_aliases = provider_config.get("model_aliases", {}) or {}
    resolved_to_alias = {str(resolved).lower(): alias for alias, resolved in model_aliases.items()}

    def tier_for_alias(alias: str) -> str | None:
        return alias_to_tier.get(alias)

    seen: set[str] = set()
    ordered: List[Tuple[str, str | None]] = []

    def add_alias(alias: str) -> None:
        alias_str = str(alias)
        alias_lower = alias_str.lower()
        if alias_lower not in alias_to_tier and alias_lower in resolved_to_alias:
            canonical = resolved_to_alias[alias_lower]
            alias_str = canonical
            alias_lower = canonical.lower()
        if alias_lower in blocked:
            logger.info("OpenRouter alias '%s' blocked by configuration", alias_str)
            return
        tier = tier_for_alias(alias_str)
        if free_only and tier != "free_trial":
            logger.debug(
                "Skipping alias '%s' (tier=%s) due to free_only selection mode",
                alias_str,
                tier,
            )
            return
        if tier == "free_trial" and not enable_free:
            logger.debug(
                "Skipping alias '%s' from free_trial tier (enable_free_models disabled)",
                alias_str,
            )
            return
        if alias_lower not in seen:
            ordered.append((alias_str, tier))
            seen.add(alias_lower)

    for entry in requested:
        if entry in capability_tiers:
            for alias in capability_tiers.get(entry, []):
                add_alias(alias)
        else:
            add_alias(entry)

    preferred_capability = preferred_capabilities.get(role)
    if preferred_capability:
        for alias in capability_tiers.get(preferred_capability, []):
            add_alias(alias)

    if free_only:
        default_tier_order = ["free_trial"]
    else:
        default_tier_order = ["finance_safe", "cost_saver", "research_heavy", "free_trial"]
    for tier in default_tier_order:
        for alias in capability_tiers.get(tier, []):
            add_alias(alias)

    return ordered


def _compute_candidate_score(
    resolved: str,
    position: int,
    total: int,
    tier: str | None,
    provider_config: Dict[str, Any],
) -> float:
    priority_component = ((total - position) / total) if total else 0.0
    profiles = provider_config.get("model_profiles", {}) or {}
    profile = profiles.get(resolved) or {}
    reliability = float(profile.get("reliability", 0.5))
    cost_weight = float(profile.get("cost_weight", 0.5))
    tier_bonus = 0.05 if tier == "finance_safe" else 0.0
    if tier == "research_heavy":
        tier_bonus += 0.02
    if tier == "cost_saver":
        tier_bonus += 0.03
    return (
        priority_component * 0.4
        + reliability * 0.4
        + cost_weight * 0.15
        + tier_bonus
    )


def _build_openrouter_candidates(
    role: str,
    requested_model: str | Sequence[str],
    provider_config: Dict[str, Any],
    logger: logging.Logger,
) -> List[ModelCandidate]:
    requested_seq = _ensure_sequence(requested_model)
    ordered_aliases = _collect_alias_candidates(role, requested_seq, provider_config, logger)
    blocked = {str(m).lower() for m in provider_config.get("blocked_models", [])}
    resolved_seen: set[str] = set()
    candidates: List[ModelCandidate] = []
    total = len(ordered_aliases) if ordered_aliases else 1

    for position, (alias, tier) in enumerate(ordered_aliases):
        resolved, cost = _resolve_model_alias(alias, "openrouter", provider_config, logger)
        resolved_lower = resolved.lower()
        if resolved_lower in blocked:
            logger.info(
                "OpenRouter model '%s' skipped because it is blocked",
                resolved,
            )
            continue
        if resolved_lower in resolved_seen:
            continue
        resolved_seen.add(resolved_lower)
        score = _compute_candidate_score(
            resolved,
            position,
            total,
            tier,
            provider_config,
        )
        candidates.append(
            ModelCandidate(
                alias=alias,
                resolved=resolved,
                cost=cost,
                score=score,
                tier=tier,
            )
        )

    if not candidates:
        raise LLMConfigurationError(
            "No OpenRouter models available after applying capability tiers and blocks."
        )
    candidates.sort(key=lambda c: c.score, reverse=True)
    return candidates


def _instantiate_openrouter_clients(
    candidates: Sequence[ModelCandidate],
    base_kwargs: Dict[str, Any],
) -> List[ChatOpenAI]:
    return [ChatOpenAI(model=candidate.resolved, **base_kwargs) for candidate in candidates]


def build_llms(config: Dict[str, Any]) -> LLMInitResult:
    """Instantiate provider-specific LLM clients for deep/quick thinking roles."""
    provider, provider_config = _resolve_provider_settings(config)
    api_key = _resolve_api_key(provider, provider_config, config)
    base_url = provider_config.get("base_url")

    deep_requested = config.get("deep_think_llm")
    quick_requested = config.get("quick_think_llm")
    if not deep_requested or not quick_requested:
        raise LLMConfigurationError(
            "Both 'deep_think_llm' and 'quick_think_llm' must be configured."
        )

    logger = logging.getLogger("tradingagents.llm")

    if provider == "openrouter":
        kwargs: Dict[str, Any] = {}
        if api_key:
            kwargs["api_key"] = api_key
        if base_url:
            kwargs["base_url"] = base_url

        deep_candidates = _build_openrouter_candidates(
            "deep_think", deep_requested, provider_config, logger
        )
        quick_candidates = _build_openrouter_candidates(
            "quick_think", quick_requested, provider_config, logger
        )

        deep_models = _instantiate_openrouter_clients(deep_candidates, kwargs)
        quick_models = _instantiate_openrouter_clients(quick_candidates, kwargs)

        rate_limit_key = "openrouter"
        max_calls = provider_config.get("max_calls_per_minute")

        deep_llm = FallbackChatModel(
            "deep_think",
            deep_candidates,
            deep_models,
            logger,
            rate_limit_key=rate_limit_key,
            max_calls_per_minute=max_calls,
        )
        quick_llm = FallbackChatModel(
            "quick_think",
            quick_candidates,
            quick_models,
            logger,
            rate_limit_key=rate_limit_key,
            max_calls_per_minute=max_calls,
        )

        deep_model = deep_candidates[0].resolved
        deep_cost = deep_candidates[0].cost
        quick_model = quick_candidates[0].resolved
        quick_cost = quick_candidates[0].cost

        logger.info(
            "OpenRouter deep_think fallback order: %s",
            " -> ".join(
                f"{candidate.resolved} (tier={candidate.tier or 'unknown'}, score={candidate.score:.2f})"
                for candidate in deep_candidates
            ),
        )
        logger.info(
            "OpenRouter quick_think fallback order: %s",
            " -> ".join(
                f"{candidate.resolved} (tier={candidate.tier or 'unknown'}, score={candidate.score:.2f})"
                for candidate in quick_candidates
            ),
        )
    elif provider in {"openai", "ollama"}:
        deep_model, deep_cost = _resolve_model_alias(
            deep_requested, provider, provider_config, logger
        )
        quick_model, quick_cost = _resolve_model_alias(
            quick_requested, provider, provider_config, logger
        )
        kwargs = {}
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
        deep_model, deep_cost = _resolve_model_alias(
            deep_requested, provider, provider_config, logger
        )
        quick_model, quick_cost = _resolve_model_alias(
            quick_requested, provider, provider_config, logger
        )
        deep_llm = ChatAnthropic(model=deep_model, **kwargs)
        quick_llm = ChatAnthropic(model=quick_model, **kwargs)
    elif provider == "google":
        kwargs = {}
        if api_key:
            kwargs["google_api_key"] = api_key
        deep_model, deep_cost = _resolve_model_alias(
            deep_requested, provider, provider_config, logger
        )
        quick_model, quick_cost = _resolve_model_alias(
            quick_requested, provider, provider_config, logger
        )
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
