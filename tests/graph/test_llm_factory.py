import types
import sys
import importlib
import importlib.util
from pathlib import Path

import pytest


class _BaseStub:
    instances = []

    def __init__(self, model, **kwargs):
        self.model = model
        self.kwargs = kwargs
        self.__class__.instances.append(self)

    @classmethod
    def reset(cls):
        cls.instances = []

    def invoke(self, *args, **kwargs):
        return types.SimpleNamespace(content="ok", model=self.model)

    def batch(self, prompts, **kwargs):
        return [self.invoke(prompt, **kwargs) for prompt in prompts]

    def bind_tools(self, tools, **kwargs):
        parent = self

        class _BoundStub:
            def invoke(self_inner, *args, **inner_kwargs):
                return parent.invoke(*args, **inner_kwargs)

            def batch(self_inner, prompts, **inner_kwargs):
                return [self_inner.invoke(p, **inner_kwargs) for p in prompts]

        return _BoundStub()


class FakeChatOpenAI(_BaseStub):
    pass


class FakeChatAnthropic(_BaseStub):
    pass


class FakeChatGoogle(_BaseStub):
    pass


def _prime_stubs():
    FakeChatOpenAI.reset()
    FakeChatAnthropic.reset()
    FakeChatGoogle.reset()


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

sys.modules["langchain_openai"] = types.SimpleNamespace(ChatOpenAI=FakeChatOpenAI)
sys.modules["langchain_anthropic"] = types.SimpleNamespace(ChatAnthropic=FakeChatAnthropic)
sys.modules["langchain_google_genai"] = types.SimpleNamespace(ChatGoogleGenerativeAI=FakeChatGoogle)
langchain_core_module = types.ModuleType("langchain_core")
runnables_module = types.ModuleType("langchain_core.runnables")


class _RunnableBase:
    def __init__(self, *args, **kwargs):
        pass


runnables_module.Runnable = _RunnableBase
sys.modules["langchain_core"] = langchain_core_module
sys.modules["langchain_core.runnables"] = runnables_module

_LLM_FACTORY_PATH = ROOT_DIR / "tradingagents" / "graph" / "llm_factory.py"
_spec = importlib.util.spec_from_file_location("tradingagents.graph.llm_factory_test", _LLM_FACTORY_PATH)
llm_factory = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader, "Unable to load llm_factory module specification"
_spec.loader.exec_module(llm_factory)

_DEFAULT_CONFIG_PATH = ROOT_DIR / "tradingagents" / "default_config.py"
_cfg_spec = importlib.util.spec_from_file_location("tradingagents.default_config_test", _DEFAULT_CONFIG_PATH)
default_config = importlib.util.module_from_spec(_cfg_spec)
assert _cfg_spec and _cfg_spec.loader, "Unable to load default_config module specification"
_cfg_spec.loader.exec_module(default_config)


def test_build_llms_openai_uses_env_and_base_url(monkeypatch):
    _prime_stubs()
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    config = default_config.copy_default_config()
    config["llm_provider"] = "openai"

    result = llm_factory.build_llms(config)

    assert result.provider == "openai"
    assert result.base_url == config["provider_config"]["openai"]["base_url"]
    assert len(FakeChatOpenAI.instances) == 2
    assert FakeChatOpenAI.instances[0].kwargs["api_key"] == "sk-test"
    assert FakeChatOpenAI.instances[0].kwargs["base_url"] == result.base_url


def test_build_llms_requires_api_key_for_openrouter(monkeypatch):
    _prime_stubs()
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    config = default_config.copy_default_config()
    config["llm_provider"] = "openrouter"
    config["provider_config"]["openrouter"]["selection_mode"] = "balanced"

    with pytest.raises(llm_factory.LLMConfigurationError):
        llm_factory.build_llms(config)


def test_build_llms_ollama_without_api_key(monkeypatch):
    _prime_stubs()
    monkeypatch.delenv("OLLAMA_API_KEY_ENV", raising=False)
    config = default_config.copy_default_config()
    config["llm_provider"] = "ollama"

    result = llm_factory.build_llms(config)

    assert len(FakeChatOpenAI.instances) == 2
    assert "api_key" not in FakeChatOpenAI.instances[0].kwargs
    assert result.base_url == config["provider_config"]["ollama"]["base_url"]


def test_build_llms_anthropic_uses_anthropic_chat(monkeypatch):
    _prime_stubs()
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-key")
    config = default_config.copy_default_config()
    config["llm_provider"] = "anthropic"

    result = llm_factory.build_llms(config)

    assert result.provider == "anthropic"
    assert len(FakeChatAnthropic.instances) == 2
    assert FakeChatAnthropic.instances[0].kwargs["api_key"] == "anthropic-key"
    assert result.base_url is None


def test_build_llms_google_uses_google_client(monkeypatch):
    _prime_stubs()
    monkeypatch.setenv("GOOGLE_API_KEY", "google-key")
    config = default_config.copy_default_config()
    config["llm_provider"] = "google"

    result = llm_factory.build_llms(config)

    assert result.provider == "google"
    assert len(FakeChatGoogle.instances) == 2
    assert FakeChatGoogle.instances[0].kwargs["google_api_key"] == "google-key"


def test_build_llms_openrouter_alias_mapping(monkeypatch, caplog):
    _prime_stubs()
    monkeypatch.setenv("OPENROUTER_API_KEY", "router-key")
    config = default_config.copy_default_config()
    config["llm_provider"] = "openrouter"
    config["deep_think_llm"] = "gpt-5-mini"
    config["quick_think_llm"] = "gpt-4o-mini"
    config["provider_config"]["openrouter"]["selection_mode"] = "balanced"

    with caplog.at_level("INFO", logger="tradingagents.llm"):
        result = llm_factory.build_llms(config)

    assert result.provider == "openrouter"
    # Fallback stacks should include finance, cost-saver, research, and free tiers.
    deep_models = [inst.model for inst in FakeChatOpenAI.instances[: len(FakeChatOpenAI.instances) // 2]]
    quick_models = [inst.model for inst in FakeChatOpenAI.instances[len(FakeChatOpenAI.instances) // 2 :]]
    deep_set = set(deep_models)
    quick_set = set(quick_models)
    expected_core = {
        "openai/gpt-5-mini",
        "openai/gpt-4o-mini",
        "mistralai/magistral-medium-2506:thinking",
        "meta-llama/llama-3.3-70b-instruct",
        "x-ai/grok-4-fast",
    }
    expected_free = {
        "z-ai/glm-4.5-air:free",
        "minimax/minimax-m2:free",
    }

    assert deep_models[0] == result.deep_llm.primary_model
    assert quick_models[0] == result.quick_llm.primary_model
    assert expected_core.issubset(deep_set)
    assert expected_core.issubset(quick_set)
    assert expected_free.issubset(deep_set)
    assert expected_free.issubset(quick_set)
    assert "Estimated OpenRouter cost" in caplog.text


def test_openrouter_respects_blocked_models(monkeypatch):
    _prime_stubs()
    monkeypatch.setenv("OPENROUTER_API_KEY", "router-key")
    config = default_config.copy_default_config()
    config["llm_provider"] = "openrouter"
    config["deep_think_llm"] = "gpt-5-mini"
    config["quick_think_llm"] = "gpt-4o-mini"
    config["provider_config"]["openrouter"]["blocked_models"] = [
        "gpt-5-mini",
        "openai/gpt-5-mini",
    ]
    config["provider_config"]["openrouter"]["selection_mode"] = "balanced"

    result = llm_factory.build_llms(config)

    assert result.deep_llm.primary_model == "openai/gpt-4o-mini"
    assert result.quick_llm.primary_model == "openai/gpt-4o-mini"


def test_openrouter_fallback_on_rate_limit(monkeypatch):
    _prime_stubs()
    monkeypatch.setenv("OPENROUTER_API_KEY", "router-key")
    config = default_config.copy_default_config()
    config["llm_provider"] = "openrouter"
    config["deep_think_llm"] = "gpt-5-mini"
    openrouter_cfg = config["provider_config"]["openrouter"]
    openrouter_cfg["selection_mode"] = "balanced"
    openrouter_cfg["model_profiles"]["openai/gpt-5-mini"]["reliability"] = 0.99
    openrouter_cfg["model_profiles"]["openai/gpt-4o-mini"]["reliability"] = 0.7

    class DummyRateLimitError(Exception):
        status_code = 429

    monkeypatch.setattr(llm_factory, "RateLimitError", DummyRateLimitError, raising=False)
    monkeypatch.setattr(llm_factory.time, "sleep", lambda _: None)

    call_counts: dict[str, int] = {}

    def invoke(self, *args, **kwargs):
        count = call_counts.get(self.model, 0) + 1
        call_counts[self.model] = count
        if self.model == "openai/gpt-5-mini" and count <= 3:
            raise DummyRateLimitError("rate limited")
        return types.SimpleNamespace(content=f"{self.model}-response", model=self.model)

    monkeypatch.setattr(FakeChatOpenAI, "invoke", invoke, raising=False)

    audit_events: list[dict[str, str]] = []
    monkeypatch.setattr(
        llm_factory,
        "emit_audit_record",
        lambda record: audit_events.append(record),
        raising=False,
    )

    result = llm_factory.build_llms(config)
    primary_model = result.deep_llm.primary_model
    fallback_model = result.deep_llm._candidates[1].resolved  # type: ignore[attr-defined]

    response = result.deep_llm.invoke("prompt")

    assert response.model == fallback_model
    assert call_counts[primary_model] == 3
    assert call_counts[fallback_model] == 1
    assert any(
        event.get("failed_model_resolved") == "openai/gpt-5-mini"
        for event in audit_events
    )


def test_openrouter_free_only_mode(monkeypatch):
    _prime_stubs()
    monkeypatch.setenv("OPENROUTER_API_KEY", "router-key")
    config = default_config.copy_default_config()
    config["llm_provider"] = "openrouter"
    config["provider_config"]["openrouter"]["selection_mode"] = "free_only"
    config["deep_think_llm"] = "deepseek-chat"
    config["quick_think_llm"] = "deepseek-chat"

    result = llm_factory.build_llms(config)

    assert result.deep_llm.primary_model in {
        "z-ai/glm-4.5-air:free",
        "minimax/minimax-m2:free",
    }
    assert result.quick_llm.primary_model in {
        "z-ai/glm-4.5-air:free",
        "minimax/minimax-m2:free",
    }
    assert len(FakeChatOpenAI.instances) == 4
    models_used = {inst.model for inst in FakeChatOpenAI.instances}
    assert models_used == {
        "z-ai/glm-4.5-air:free",
        "minimax/minimax-m2:free",
    }
