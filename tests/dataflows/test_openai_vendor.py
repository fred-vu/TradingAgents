import sys
import types
import importlib
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from tradingagents.dataflows.config import set_config, get_config


class DummyResponses:
    next_response = None
    last_kwargs = None

    def create(self, **kwargs):
        DummyResponses.last_kwargs = kwargs
        if DummyResponses.next_response is None:
            raise AssertionError("next_response not set")
        return DummyResponses.next_response


class DummyOpenAI:
    def __init__(self, base_url=None):
        self.base_url = base_url
        self.responses = DummyResponses()


sys.modules["openai"] = types.SimpleNamespace(OpenAI=DummyOpenAI)

openai_vendor = importlib.import_module("tradingagents.dataflows.openai")


class ResponseWithOutputText:
    def __init__(self, text):
        self.output_text = text


class ResponseWithOutputBlocks:
    class _Content:
        def __init__(self, text):
            self.text = text

    class _Block:
        def __init__(self, text):
            self.content = [ResponseWithOutputBlocks._Content(text)]

    def __init__(self, text):
        self.output = [ResponseWithOutputBlocks._Block(text)]


def test_get_stock_news_prefers_output_text(monkeypatch):
    DummyResponses.next_response = ResponseWithOutputText("news-summary")
    set_config({})

    result = openai_vendor.get_stock_news_openai("NVDA", "2024-01-01", "2024-01-07")

    assert result == "news-summary"
    assert DummyResponses.last_kwargs["model"] == get_config()["quick_think_llm"]


def test_get_global_news_falls_back_to_output_blocks(monkeypatch):
    DummyResponses.next_response = ResponseWithOutputBlocks("macro-news")
    set_config({})

    result = openai_vendor.get_global_news_openai("2024-01-07")

    assert result == "macro-news"


def test_get_fundamentals_raises_when_no_text():
    DummyResponses.next_response = object()
    set_config({})

    with pytest.raises(RuntimeError):
        openai_vendor.get_fundamentals_openai("NVDA", "2024-01-07")
