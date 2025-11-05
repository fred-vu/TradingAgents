"""
Pydantic models used by the TradingAgents FastAPI backend.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class AnalyzeRequest(BaseModel):
    """Request payload for `/api/analyze`."""

    symbol: str = Field(
        ...,
        min_length=1,
        max_length=12,
        description="Equity ticker symbol (AAPL, MSFT, etc.)",
    )
    lookback_days: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Historical lookback window in days.",
    )
    strategy: str = Field(
        default="balanced",
        min_length=1,
        max_length=32,
        description="Trading strategy preference (balanced, aggressive, etc.).",
    )

    @field_validator("symbol", mode="before")
    def normalise_symbol(cls, value: str) -> str:
        """Ensure symbols are uppercased and trimmed."""
        if value is None:
            return value
        return value.strip().upper()

    @field_validator("strategy", mode="before")
    def normalise_strategy(cls, value: str) -> str:
        if value is None:
            return value
        return value.strip().lower()


class AnalystResponse(BaseModel):
    """Individual analyst output from the debate pipeline."""

    name: str = Field(..., description="Analyst identifier (market/news/...)")
    signal: str = Field(
        ...,
        description="Analyst directional signal (BULLISH/BEARISH/NEUTRAL).",
    )
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str = Field(..., description="Rationale supporting the signal.")


class TradeRecommendation(BaseModel):
    """Aggregated trading recommendation exposed to clients."""

    symbol: str
    recommendation: str = Field(..., description="BUY, SELL, HOLD, etc.")
    confidence: float = Field(..., ge=0.0, le=1.0)
    risk_score: float = Field(..., ge=0.0, le=1.0)
    analysts: List[AnalystResponse]
    debate_rounds: int = Field(..., ge=0)
    trader_notes: str
    timestamp: datetime


class HealthResponse(BaseModel):
    """Response model for `/api/health`."""

    status: str
    version: str
    uptime_seconds: float
    last_analysis: Optional[datetime] = None
    error: Optional[str] = None


class ConfigResponse(BaseModel):
    """Subset of configuration exposed to the desktop client."""

    llm_provider: str
    data_vendors: List[str]
    max_debate_rounds: int
    min_confidence_threshold: float


class MetricsResponse(BaseModel):
    """Aggregate performance metrics consumed by the dashboard."""

    accuracy: float = Field(..., ge=0.0, le=1.0)
    win_rate: float = Field(..., ge=0.0, le=1.0)
    avg_confidence: float = Field(..., ge=0.0, le=1.0)
    sharpe_ratio: Optional[float] = Field(None)
    monthly_performance: List[Dict[str, Any]] = Field(default_factory=list)
