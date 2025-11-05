"""
Application service orchestrating trading analyses for the FastAPI backend.
"""

from __future__ import annotations

import asyncio
import csv
import hashlib
import json
import logging
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import List, Optional

from tradingagents.app.models.trade import AnalystResponse, TradeRecommendation

logger = logging.getLogger(__name__)


class TradingService:
    """
    Facade over the trading graph. The service currently supports a mock mode
    (default) that produces deterministic recommendations suitable for UI
    development and automated testing. Set the environment variable
    `TRADINGAGENTS_BACKEND_MODE=real` to initialise the full LangGraph-powered
    pipeline once API credentials are available.
    """

    def __init__(self) -> None:
        self.start_time: datetime = datetime.now(UTC)
        self.last_analysis_time: Optional[datetime] = None
        self.analysis_history: List[TradeRecommendation] = []

        self._mode = os.getenv("TRADINGAGENTS_BACKEND_MODE", "mock").lower()
        self._history_lock = asyncio.Lock()
        self._graph_lock = asyncio.Lock()
        self._graph = None  # lazy import when `real` mode enabled

        cache_root = os.getenv("TRADINGAGENTS_CACHE_DIR")
        self._cache_dir = Path(cache_root) if cache_root else Path(".cache")
        self._cache_dir.mkdir(parents=True, exist_ok=True)

        logger.info("TradingService initialised (mode=%s)", self._mode)

    async def run_analysis(
        self,
        *,
        symbol: str,
        lookback_days: int,
        strategy: str,
    ) -> TradeRecommendation:
        """Execute the trading pipeline for the requested symbol."""

        normalised_symbol = symbol.strip().upper()
        if not normalised_symbol:
            raise ValueError("Symbol must not be empty.")
        if lookback_days < 1:
            raise ValueError("lookback_days must be >= 1.")

        if self._mode == "real":
            result = await self._run_real_analysis(
                symbol=normalised_symbol,
                lookback_days=lookback_days,
                strategy=strategy,
            )
        else:
            result = self._run_mock_analysis(
                symbol=normalised_symbol,
                lookback_days=lookback_days,
                strategy=strategy,
            )

        async with self._history_lock:
            self.analysis_history.append(result)
            self.last_analysis_time = result.timestamp

        return result

    async def get_history(
        self,
        *,
        symbol: Optional[str] = None,
        days: int = 30,
        limit: int = 50,
    ) -> List[TradeRecommendation]:
        """Return cached recommendations filtered by age and symbol."""

        cutoff = datetime.now(UTC) - timedelta(days=days)
        symbol = symbol.strip().upper() if symbol else None

        async with self._history_lock:
            candidates = list(self.analysis_history)

        filtered = [
            rec
            for rec in reversed(candidates)
            if rec.timestamp >= cutoff and (symbol is None or rec.symbol == symbol)
        ]
        return filtered[:limit]

    async def export_history(
        self,
        *,
        symbol: Optional[str] = None,
        format: str = "csv",
        days: int = 90,
    ) -> str:
        """
        Export historical recommendations to disk and return the file path.
        """

        history = await self.get_history(symbol=symbol, days=days, limit=1000)
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        safe_symbol = symbol or "all"
        format = format.lower()

        if format not in {"csv", "json"}:
            raise ValueError("format must be either 'csv' or 'json'.")

        file_path = self._cache_dir / f"trades_{safe_symbol}_{timestamp}.{format}"

        if format == "json":
            payload = [rec.model_dump(mode="json") for rec in history]
            file_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        else:
            with file_path.open("w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow(
                    [
                        "symbol",
                        "recommendation",
                        "confidence",
                        "risk_score",
                        "debate_rounds",
                        "timestamp",
                    ]
                )
                for rec in history:
                    writer.writerow(
                        [
                            rec.symbol,
                            rec.recommendation,
                            f"{rec.confidence:.4f}",
                            f"{rec.risk_score:.4f}",
                            rec.debate_rounds,
                            rec.timestamp.isoformat(),
                        ]
                    )

        logger.info("Exported %s records to %s", len(history), file_path)
        return str(file_path)

    async def compute_metrics(self, *, days: int = 30) -> dict:
        """Derive lightweight performance metrics from cached history."""

        history = await self.get_history(days=days, limit=1000)
        if not history:
            return {
                "accuracy": 0.0,
                "win_rate": 0.0,
                "avg_confidence": 0.0,
                "sharpe_ratio": None,
                "monthly_performance": [],
            }

        buy_signals = sum(1 for rec in history if rec.recommendation == "BUY")
        sell_signals = sum(1 for rec in history if rec.recommendation == "SELL")
        win_rate = buy_signals / len(history)
        avg_confidence = sum(rec.confidence for rec in history) / len(history)

        monthly_totals: dict[str, int] = {}
        for rec in history:
            key = rec.timestamp.strftime("%Y-%m")
            monthly_totals[key] = monthly_totals.get(key, 0) + 1

        monthly_performance = [
            {"month": month, "signals": count}
            for month, count in sorted(monthly_totals.items())
        ]

        return {
            "accuracy": max(0.0, min(1.0, (buy_signals + sell_signals) / (len(history) or 1))),
            "win_rate": max(0.0, min(1.0, win_rate)),
            "avg_confidence": max(0.0, min(1.0, avg_confidence)),
            "sharpe_ratio": None,
            "monthly_performance": monthly_performance,
        }

    async def shutdown(self) -> None:
        """Placeholder for releasing external resources."""
        logger.info("TradingService shutdown complete.")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run_mock_analysis(
        self,
        *,
        symbol: str,
        lookback_days: int,
        strategy: str,
    ) -> TradeRecommendation:
        """Produce deterministic yet varied mock data for the UI."""

        digest = hashlib.sha256(
            f"{symbol}:{lookback_days}:{strategy}".encode("utf-8")
        ).hexdigest()
        sample = int(digest[:8], 16) / 0xFFFFFFFF

        confidence = 0.45 + (sample * 0.45)
        risk_score = max(0.05, 1.0 - confidence * 0.8)

        options = ["BUY", "HOLD", "SELL"]
        recommendation = options[int(sample * len(options)) % len(options)]

        analyst_templates = [
            ("market_analyst", "Market trend assessment."),
            ("news_analyst", "Headline sentiment summary."),
            ("fundamental_analyst", "Earnings and valuation review."),
        ]

        analysts = [
            AnalystResponse(
                name=name,
                signal=recommendation if idx == 0 else options[(idx + int(sample * 3)) % len(options)],
                confidence=max(0.3, min(0.95, confidence - idx * 0.1)),
                reasoning=text,
            )
            for idx, (name, text) in enumerate(analyst_templates)
        ]

        timestamp = datetime.now(UTC)
        debate_rounds = max(1, min(3, lookback_days // 15))
        trader_notes = (
            f"Mock {strategy} strategy evaluation for {symbol}. "
            f"Confidence at {confidence:.2%}, risk score {risk_score:.2f}."
        )

        return TradeRecommendation(
            symbol=symbol,
            recommendation=recommendation,
            confidence=max(0.0, min(1.0, confidence)),
            risk_score=max(0.0, min(1.0, risk_score)),
            analysts=analysts,
            debate_rounds=debate_rounds,
            trader_notes=trader_notes,
            timestamp=timestamp,
        )

    async def _run_real_analysis(
        self,
        *,
        symbol: str,
        lookback_days: int,
        strategy: str,
    ) -> TradeRecommendation:
        """
        Execute the LangGraph-powered pipeline. This path is intentionally
        isolated so it can be enabled once credentials are provisioned.
        """

        graph = await self._ensure_graph()
        loop = asyncio.get_running_loop()
        trade_date = datetime.now(UTC).date().isoformat()

        final_state, processed_signal = await loop.run_in_executor(
            None, lambda: graph.propagate(symbol, trade_date)
        )
        recommendation = processed_signal.upper()

        analysts = [
            AnalystResponse(
                name="market_analyst",
                signal=final_state.get("market_signal", recommendation),
                confidence=0.6,
                reasoning=final_state.get("market_report", ""),
            ),
            AnalystResponse(
                name="news_analyst",
                signal="NEUTRAL",
                confidence=0.5,
                reasoning=final_state.get("news_report", ""),
            ),
            AnalystResponse(
                name="fundamental_analyst",
                signal="NEUTRAL",
                confidence=0.5,
                reasoning=final_state.get("fundamentals_report", ""),
            ),
        ]

        return TradeRecommendation(
            symbol=symbol,
            recommendation=recommendation,
            confidence=final_state.get("confidence", 0.5),
            risk_score=final_state.get("risk_score", 0.5),
            analysts=analysts,
            debate_rounds=final_state.get("investment_debate_state", {}).get("count", 1),
            trader_notes=final_state.get("trader_investment_plan", ""),
            timestamp=datetime.now(UTC),
        )

    async def _ensure_graph(self):
        """Lazy initialise the trading graph in `real` mode."""

        if self._graph is None:
            async with self._graph_lock:
                if self._graph is None:
                    logger.info("Initialising TradingAgentsGraph (real mode)...")
                    loop = asyncio.get_running_loop()
                    self._graph = await loop.run_in_executor(None, self._create_graph)
        return self._graph

    @staticmethod
    def _create_graph():
        """Blocking factory executed inside a background thread."""
        from tradingagents.default_config import copy_default_config
        from tradingagents.graph.trading_graph import TradingAgentsGraph

        config = copy_default_config()
        return TradingAgentsGraph(debug=False, config=config)
