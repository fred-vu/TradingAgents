"""Unit tests for the TradingAgents FastAPI backend."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tradingagents.app.backend import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def test_health_check(client: TestClient) -> None:
    response = client.get("/api/health")
    data = response.json()
    assert response.status_code == 200
    assert data["status"] == "ok"
    assert data["version"] == "1.0.0"
    assert "uptime_seconds" in data


def test_status_endpoint(client: TestClient) -> None:
    response = client.get("/api/status")
    payload = response.json()
    assert response.status_code == 200
    assert "pending_jobs" in payload
    assert payload["system_status"] == "healthy"
    assert "last_analysis" in payload


def test_analyze_valid_request(client: TestClient) -> None:
    response = client.post(
        "/api/analyze",
        json={"symbol": "AAPL", "lookback_days": 30, "strategy": "balanced"},
    )
    data = response.json()
    assert response.status_code == 200
    assert data["symbol"] == "AAPL"
    assert data["recommendation"] in {"BUY", "HOLD", "SELL"}
    assert 0.0 <= data["confidence"] <= 1.0
    assert len(data["analysts"]) >= 1
    assert isinstance(data["price_series"], list)
    if data["price_series"]:
        assert data["price_series"][0]["value"] > 0
    assert isinstance(data["debate_history"], list)
    assert isinstance(data["key_insights"], list)


def test_analyze_invalid_symbol(client: TestClient) -> None:
    response = client.post(
        "/api/analyze",
        json={"symbol": "", "lookback_days": 30},
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"][-1] == "symbol"
    assert response.json()["detail"][0]["type"] == "string_too_short"


def test_analyze_invalid_lookback(client: TestClient) -> None:
    response = client.post(
        "/api/analyze",
        json={"symbol": "AAPL", "lookback_days": 0},
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"][-1] == "lookback_days"
    assert response.json()["detail"][0]["type"] == "greater_than_equal"


def test_config_roundtrip(client: TestClient) -> None:
    current = client.get("/api/config").json()
    assert current["llm_provider"]
    assert isinstance(current["data_vendors"], list)

    response = client.post(
        "/api/config",
        json={"llm_provider": "anthropic", "min_confidence_threshold": 0.55},
    )
    updated = response.json()
    assert response.status_code == 200
    assert updated["status"] == "saved"
    assert updated["config"]["llm_provider"] == "anthropic"


def test_metrics_history_flow(client: TestClient) -> None:
    client.post("/api/analyze", json={"symbol": "MSFT", "lookback_days": 45})

    history_response = client.get("/api/history")
    history = history_response.json()
    assert history_response.status_code == 200
    assert len(history) >= 1
    assert history[0]["symbol"] in {"AAPL", "MSFT"}

    metrics_response = client.get("/api/metrics", params={"days": 60})
    metrics = metrics_response.json()
    assert metrics_response.status_code == 200
    assert 0.0 <= metrics["avg_confidence"] <= 1.0
    assert "monthly_performance" in metrics
    assert isinstance(metrics["monthly_performance"], list)
    assert "equity_curve" in metrics and isinstance(metrics["equity_curve"], list)
    assert "recommendation_distribution" in metrics
    assert sum(metrics["recommendation_distribution"].values()) >= 1


def test_export_history(client: TestClient) -> None:
    response = client.get("/api/export", params={"format": "json", "days": 120})
    payload = response.json()
    exported_path = Path(payload["file_path"])
    assert response.status_code == 200
    assert payload["format"] == "json"
    assert exported_path.exists()


def test_export_history_download(client: TestClient) -> None:
    response = client.get(
        "/api/export/download",
        params={"format": "csv", "days": 30},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers.get("content-disposition", "")
