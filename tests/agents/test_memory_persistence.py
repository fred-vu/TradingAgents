import sys
import types
import importlib.util
from pathlib import Path

import pytest


class DummyEmbeddingsResponse:
    def __init__(self):
        self.data = [types.SimpleNamespace(embedding=[0.1, 0.2, 0.3])]


class DummyOpenAI:
    def __init__(self, base_url=None):
        self.base_url = base_url
        self.embeddings = self

    def create(self, model, input):
        return DummyEmbeddingsResponse()


class DummyCollection:
    def __init__(self):
        self._count = 0
        self.add_calls = []

    def count(self):
        return self._count

    def add(self, documents, metadatas, embeddings, ids):
        self._count += len(documents)
        self.add_calls.append(
            {
                "documents": documents,
                "metadatas": metadatas,
                "embeddings": embeddings,
                "ids": ids,
            }
        )

    def query(self, query_embeddings, n_results, include):
        return {
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }


class DummyChromaClient:
    def __init__(self, settings=None, path=None):
        self.settings = settings
        self.path = path
        self.persist_called = False
        self.collection = DummyCollection()

    def get_or_create_collection(self, name):
        self.collection.name = name
        return self.collection

    def persist(self):
        self.persist_called = True


@pytest.fixture(autouse=True)
def patch_dependencies(monkeypatch):
    monkeypatch.setitem(
        sys.modules,
        "chromadb",
        types.SimpleNamespace(Client=DummyChromaClient, PersistentClient=DummyChromaClient),
    )
    monkeypatch.setitem(
        sys.modules,
        "chromadb.config",
        types.SimpleNamespace(Settings=lambda **kwargs: kwargs),
    )
    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=DummyOpenAI))
    yield
    sys.modules.pop("chromadb", None)
    sys.modules.pop("chromadb.config", None)
    sys.modules.pop("openai", None)


def load_memory_module():
    module_path = Path(__file__).resolve().parents[2] / "tradingagents" / "agents" / "utils" / "memory.py"
    spec = importlib.util.spec_from_file_location("memory_module", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_financial_memory_uses_persist_directory(tmp_path):
    memory_module = load_memory_module()
    config = {
        "backend_url": "https://api.openai.com/v1",
        "memory_dir": str(tmp_path),
    }
    memory = memory_module.FinancialSituationMemory("test_collection", config)

    assert memory.persist_directory == str(tmp_path)
    client = memory.chroma_client
    assert isinstance(client, DummyChromaClient)
    if client.settings is not None:
        assert client.settings["persist_directory"] == str(tmp_path)
    else:
        assert client.path == str(tmp_path)
    assert client.collection.name == "test_collection"


def test_financial_memory_persists_after_add(tmp_path):
    memory_module = load_memory_module()
    config = {
        "backend_url": "https://api.openai.com/v1",
        "memory_dir": str(tmp_path),
    }
    memory = memory_module.FinancialSituationMemory("test_collection", config)
    client = memory.chroma_client

    memory.add_situations([("situation", "advice")])

    assert client.collection.count() == 1
    assert client.persist_called is True
