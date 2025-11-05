"""
Development entry point for the TradingAgents FastAPI backend.
"""

from __future__ import annotations

import argparse

from tradingagents.app.backend import run_server


def main() -> None:
    parser = argparse.ArgumentParser(description="Run TradingAgents FastAPI backend")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address")
    parser.add_argument("--port", type=int, default=8000, help="Port number")
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload (development only)",
    )
    args = parser.parse_args()
    run_server(host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()

