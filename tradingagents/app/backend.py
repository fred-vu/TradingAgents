"""
FastAPI backend for the TradingAgents desktop application.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional, Set

import uvicorn
from fastapi import Body, FastAPI, HTTPException, Query, WebSocket
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.websockets import WebSocketDisconnect

from tradingagents.app.models.trade import (
    AnalyzeRequest,
    ConfigResponse,
    HealthResponse,
    MetricsResponse,
    TradeRecommendation,
)
from tradingagents.app.services.config_service import ConfigService
from tradingagents.app.services.trading_service import TradingService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tradingagents.app.backend")

trading_service: Optional[TradingService] = None
config_service: Optional[ConfigService] = None
active_connections: Set[WebSocket] = set()
_broadcast_lock = asyncio.Lock()


async def _broadcast(message: dict) -> None:
    """Send a JSON payload to all connected WebSocket clients."""
    if not active_connections:
        return

    payload = jsonable_encoder(message)
    async with _broadcast_lock:
        coros = [connection.send_json(payload) for connection in list(active_connections)]
        results = await asyncio.gather(*coros, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                logger.debug("WebSocket broadcast exception: %s", result)


async def _build_status_payload() -> dict:
    return {
        "type": "status_update",
        "timestamp": datetime.now(UTC).isoformat(),
        "last_analysis": trading_service.last_analysis_time.isoformat()
        if trading_service and trading_service.last_analysis_time
        else None,
    }


@asynccontextmanager
async def _lifespan(app: FastAPI):
    global trading_service, config_service

    logger.info("Starting TradingAgents FastAPI backend...")
    trading_service = TradingService()
    config_service = ConfigService()
    logger.info("Services initialised.")

    try:
        yield
    finally:
        logger.info("Shutting down TradingAgents backend...")
        if trading_service:
            await trading_service.shutdown()
        logger.info("Shutdown complete.")


app = FastAPI(
    title="TradingAgents API",
    version="1.0.0",
    description="TradingAgents backend service",
    lifespan=_lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://127.0.0.1", "tauri://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Simple service health probe."""
    try:
        uptime = (
            (datetime.now(UTC) - trading_service.start_time).total_seconds()
            if trading_service
            else 0.0
        )
        return HealthResponse(
            status="ok",
            version="1.0.0",
            uptime_seconds=uptime,
            last_analysis=trading_service.last_analysis_time
            if trading_service
            else None,
        )
    except Exception as exc:  # pragma: no cover - defensive path
        logger.error("Health check failure: %s", exc, exc_info=True)
        return HealthResponse(
            status="error",
            version="1.0.0",
            uptime_seconds=0.0,
            error=str(exc),
        )


@app.get("/api/status")
async def status() -> dict:
    """Return lightweight service status information."""
    return {
        "last_analysis": trading_service.last_analysis_time.isoformat()
        if trading_service and trading_service.last_analysis_time
        else None,
        "pending_jobs": 0,
        "memory_mb": 0,
        "system_status": "healthy",
    }


@app.post("/api/analyze", response_model=TradeRecommendation)
async def analyze(request: AnalyzeRequest) -> TradeRecommendation:
    """Run trading analysis for a symbol."""
    logger.info("Analyse request received: %s", request.symbol)
    try:
        result = await trading_service.run_analysis(
            symbol=request.symbol,
            lookback_days=request.lookback_days,
            strategy=request.strategy,
        )
        await _broadcast({"type": "analysis_complete", "payload": result.model_dump()})
        return result
    except ValueError as exc:
        logger.warning("Invalid analyse request: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive path
        logger.error("Analysis failure: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Analysis failed.") from exc


@app.get("/api/history", response_model=list[TradeRecommendation])
async def get_history(
    symbol: Optional[str] = Query(default=None),
    days: int = Query(default=30, ge=1, le=365),
    limit: int = Query(default=50, ge=1, le=500),
) -> list[TradeRecommendation]:
    """Return historical recommendations."""
    try:
        return await trading_service.get_history(symbol=symbol, days=days, limit=limit)
    except Exception as exc:  # pragma: no cover - defensive path
        logger.error("History retrieval failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="History retrieval failed.") from exc


@app.get("/api/export")
async def export_history(
    symbol: Optional[str] = Query(default=None),
    format: str = Query(default="csv", pattern="^(csv|json)$"),
    days: int = Query(default=90, ge=1, le=365),
) -> dict:
    """Export cached history to disk."""
    try:
        file_path = await trading_service.export_history(
            symbol=symbol, format=format, days=days
        )
        return {"file_path": file_path, "format": format}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive path
        logger.error("History export failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Export failed.") from exc


@app.get("/api/export/download")
async def export_history_download(
    symbol: Optional[str] = Query(default=None),
    format: str = Query(default="csv", pattern="^(csv|json)$"),
    days: int = Query(default=90, ge=1, le=365),
) -> FileResponse:
    try:
        file_path = await trading_service.export_history(
            symbol=symbol, format=format, days=days
        )
        media_type = "text/csv" if format == "csv" else "application/json"
        filename = Path(file_path).name
        return FileResponse(path=file_path, media_type=media_type, filename=filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive path
        logger.error("History export download failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Export download failed.") from exc


@app.get("/api/config", response_model=ConfigResponse)
async def get_config() -> ConfigResponse:
    """Return persisted configuration."""
    try:
        return config_service.get_config()
    except Exception as exc:  # pragma: no cover - defensive path
        logger.error("Config retrieval failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Config retrieval failed.") from exc


@app.post("/api/config")
async def update_config(updates: dict = Body(...)) -> dict:
    """Update persisted configuration."""
    logger.info("Config update request: %s", ", ".join(updates.keys()))
    try:
        config_service.update_config(updates)
        return {"status": "saved", "config": config_service.get_config()}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive path
        logger.error("Config update failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Config update failed.") from exc


@app.post("/api/config/test-connection")
async def test_connection(payload: dict = Body(...)) -> dict:
    """Test connectivity to a configured data vendor."""
    vendor = payload.get("vendor")
    if not vendor:
        raise HTTPException(status_code=400, detail="Missing 'vendor' in payload.")
    try:
        return await config_service.test_vendor_connection(vendor)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive path
        logger.error("Vendor test failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Vendor test failed.") from exc


@app.get("/api/metrics", response_model=MetricsResponse)
async def get_metrics(days: int = Query(default=30, ge=1, le=365)) -> MetricsResponse:
    """Return aggregated performance metrics."""
    try:
        metrics = await trading_service.compute_metrics(days=days)
        return MetricsResponse(**metrics)
    except Exception as exc:  # pragma: no cover - defensive path
        logger.error("Metrics computation failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Metrics computation failed.") from exc


@app.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Provide a simple status stream for the desktop client."""
    await websocket.accept()
    active_connections.add(websocket)
    logger.info("WebSocket connected (total=%s)", len(active_connections))

    try:
        while True:
            await websocket.send_json(await _build_status_payload())
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected.")
    except Exception as exc:  # pragma: no cover - defensive path
        logger.error("WebSocket exception: %s", exc, exc_info=True)
    finally:
        active_connections.discard(websocket)
        logger.info("Active WebSocket connections: %s", len(active_connections))


def run_server(host: str = "127.0.0.1", port: int = 8000, reload: bool = False) -> None:
    """Convenience entry point used by run_backend.py."""
    logger.info("Launching FastAPI server on %s:%s (reload=%s)", host, port, reload)
    uvicorn.run(
        "tradingagents.app.backend:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )
