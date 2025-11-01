import logging
from pathlib import Path

import chromadb
from chromadb.config import Settings
from openai import OpenAI


class FinancialSituationMemory:
    def __init__(self, name, config):
        self.logger = logging.getLogger("tradingagents.memory")
        self.name = name
        backend_url = config.get("backend_url", "https://api.openai.com/v1")
        if backend_url == "http://localhost:11434/v1":
            self.embedding = "nomic-embed-text"
        else:
            self.embedding = "text-embedding-3-small"

        self.client = OpenAI(base_url=backend_url)

        persist_directory = Path(
            config.get("memory_dir") or config.get("data_cache_dir") or "."
        ).expanduser()
        persist_directory.mkdir(parents=True, exist_ok=True)
        self.persist_directory = str(persist_directory)

        settings = Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=self.persist_directory,
            anonymized_telemetry=False,
            allow_reset=False,
        )

        self.chroma_client = chromadb.Client(settings)
        try:
            self.situation_collection = self.chroma_client.get_or_create_collection(name=name)
        except AttributeError:
            try:
                self.situation_collection = self.chroma_client.get_collection(name=name)
            except Exception:
                self.situation_collection = self.chroma_client.create_collection(name=name)

        self.logger.debug(
            "Initialized memory collection '%s' at %s using embedding model %s",
            name,
            self.persist_directory,
            self.embedding,
        )

    def get_embedding(self, text):
        """Get OpenAI embedding for a text."""
        response = self.client.embeddings.create(model=self.embedding, input=text)
        return response.data[0].embedding

    def add_situations(self, situations_and_advice):
        """Add financial situations and their corresponding advice."""
        if not situations_and_advice:
            return

        offset = self.situation_collection.count()
        documents = []
        advice = []
        ids = []
        embeddings = []

        for i, (situation, recommendation) in enumerate(situations_and_advice):
            documents.append(situation)
            advice.append(recommendation)
            ids.append(str(offset + i))
            embeddings.append(self.get_embedding(situation))

        self.situation_collection.add(
            documents=documents,
            metadatas=[{"recommendation": rec} for rec in advice],
            embeddings=embeddings,
            ids=ids,
        )

        if hasattr(self.chroma_client, "persist"):
            try:
                self.chroma_client.persist()
            except Exception:
                self.logger.debug("Chroma client persist() failed; continuing without persistence.", exc_info=True)

        self.logger.debug(
            "Persisted %d situations to collection '%s'",
            len(situations_and_advice),
            self.name,
        )

    def get_memories(self, current_situation, n_matches=1):
        """Find matching recommendations using OpenAI embeddings."""
        if self.situation_collection.count() == 0:
            return []

        query_embedding = self.get_embedding(current_situation)

        results = self.situation_collection.query(
            query_embeddings=[query_embedding],
            n_results=n_matches,
            include=["metadatas", "documents", "distances"],
        )

        matches = []
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for doc, metadata, distance in zip(documents, metadatas, distances):
            matches.append(
                {
                    "matched_situation": doc,
                    "recommendation": metadata.get("recommendation"),
                    "similarity_score": 1 - distance,
                }
            )

        return matches
