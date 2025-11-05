"""
Configuration service used by the FastAPI backend.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from tradingagents.app.models.trade import ConfigResponse
from tradingagents.default_config import copy_default_config

logger = logging.getLogger(__name__)


class ConfigService:
    """Manage persisted settings exposed to the desktop client."""

    def __init__(self, config_path: Optional[Path] = None) -> None:
        base_dir = os.getenv("TRADINGAGENTS_CONFIG_DIR")
        self._config_dir = Path(base_dir) if base_dir else Path(".tradingagents")
        self._config_dir.mkdir(parents=True, exist_ok=True)

        self._config_path = config_path or self._config_dir / "config.json"
        self.config: Dict[str, Any] = self._load_config()
        logger.info("ConfigService initialised at %s", self._config_path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_config(self) -> ConfigResponse:
        """Return strongly typed configuration for API clients."""
        return ConfigResponse(
            llm_provider=str(self.config.get("llm_provider", "openai")),
            data_vendors=list(self.config.get("data_vendors", [])),
            max_debate_rounds=int(self.config.get("max_debate_rounds", 1)),
            min_confidence_threshold=float(
                self.config.get("min_confidence_threshold", 0.5)
            ),
        )

    def update_config(self, updates: Dict[str, Any]) -> None:
        """Persist validated configuration updates."""
        if not isinstance(updates, dict):
            raise ValueError("Updates payload must be a dictionary.")

        merged = dict(self.config)

        for key, value in updates.items():
            if key == "llm_provider":
                merged[key] = str(value).strip()
            elif key == "data_vendors":
                if not isinstance(value, (list, tuple)):
                    raise ValueError("data_vendors must be a list of strings.")
                merged[key] = [str(v).strip() for v in value if str(v).strip()]
            elif key == "max_debate_rounds":
                rounds = int(value)
                if rounds < 1:
                    raise ValueError("max_debate_rounds must be >= 1.")
                merged[key] = rounds
            elif key == "min_confidence_threshold":
                threshold = float(value)
                if not 0.0 <= threshold <= 1.0:
                    raise ValueError("min_confidence_threshold must be between 0 and 1.")
                merged[key] = threshold
            else:
                merged[key] = value

        self.config = merged
        self._save_config(self.config)
        logger.info("Config updated with keys: %s", ", ".join(updates.keys()))

    async def test_vendor_connection(self, vendor: str) -> Dict[str, Any]:
        """
        Stubbed data vendor test endpoint. Once vendor SDKs are wired in we can
        replace this with real connectivity checks.
        """

        vendor = vendor.strip()
        if not vendor:
            raise ValueError("Vendor name must not be empty.")

        registered_vendors = set(self.config.get("data_vendors", []))
        status = (
            "connected"
            if not registered_vendors or vendor in registered_vendors
            else "unknown_vendor"
        )
        message = (
            f"Connection to {vendor} successful"
            if status == "connected"
            else f"{vendor} is not present in the configured data vendors list"
        )
        return {"status": status, "vendor": vendor, "message": message}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_config(self) -> Dict[str, Any]:
        if self._config_path.exists():
            try:
                with self._config_path.open("r", encoding="utf-8") as fh:
                    return json.load(fh)
            except json.JSONDecodeError as exc:
                logger.warning(
                    "Config file %s is corrupted (%s). Rebuilding defaults.",
                    self._config_path,
                    exc,
                )

        defaults = self._build_defaults()
        self._save_config(defaults)
        return defaults

    def _save_config(self, config: Dict[str, Any]) -> None:
        with self._config_path.open("w", encoding="utf-8") as fh:
            json.dump(config, fh, indent=2)

    @staticmethod
    def _build_defaults() -> Dict[str, Any]:
        base_config = copy_default_config()
        vendor_values = list(dict.fromkeys(base_config.get("data_vendors", {}).values()))
        vendor_values = [v for v in vendor_values if v]

        return {
            "llm_provider": base_config.get("llm_provider", "openai"),
            "data_vendors": vendor_values or ["yfinance"],
            "max_debate_rounds": int(base_config.get("max_debate_rounds", 1)),
            "min_confidence_threshold": 0.5,
            "auto_refresh_interval": 15,
            "notifications_enabled": True,
        }

