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
    config["deep_think_llm"] = "gpt-4-turbo"
    config["quick_think_llm"] = "gpt-4o-mini"

    with caplog.at_level("INFO", logger="tradingagents.llm"):
        result = llm_factory.build_llms(config)

    assert result.provider == "openrouter"
    assert len(FakeChatOpenAI.instances) == 2
    deep_model_used = FakeChatOpenAI.instances[0].model
    quick_model_used = FakeChatOpenAI.instances[1].model
    assert deep_model_used == "openai/gpt-4-turbo"
    assert quick_model_used == "openai/gpt-4o-mini"
    assert "Estimated OpenRouter cost" in caplog.text
