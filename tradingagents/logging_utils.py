import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

_LOGGING_INITIALISED = False
_LOGGING_LOCK = threading.Lock()


def init_logging(config: Dict[str, Any]) -> None:
    """Initialise structured logging for the TradingAgents package."""
    global _LOGGING_INITIALISED
    if _LOGGING_INITIALISED:
        return

    with _LOGGING_LOCK:
        if _LOGGING_INITIALISED:
            return

        log_dir = Path(config.get("log_dir", "./logs")).expanduser()
        log_dir.mkdir(parents=True, exist_ok=True)

        log_level = str(config.get("log_level", "INFO")).upper()
        level = getattr(logging, log_level, logging.INFO)

        log_file = log_dir / "tradingagents.log"
        audit_file = log_dir / config.get("audit_log_filename", "trade_audit.jsonl")

        formatter = logging.Formatter(
            "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        core_logger = logging.getLogger("tradingagents")
        core_logger.setLevel(level)

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        core_logger.addHandler(file_handler)

        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(level)
        stream_handler.setFormatter(formatter)
        core_logger.addHandler(stream_handler)

        audit_logger = logging.getLogger("tradingagents.audit")
        audit_logger.setLevel(logging.INFO)
        audit_handler = logging.FileHandler(audit_file, encoding="utf-8")
        audit_handler.setLevel(logging.INFO)
        audit_handler.setFormatter(logging.Formatter("%(message)s"))
        audit_logger.addHandler(audit_handler)
        audit_logger.propagate = False

        _LOGGING_INITIALISED = True


def reset_logging_for_tests() -> None:
    """Reset logging state so tests can reinitialise handlers."""
    global _LOGGING_INITIALISED
    with _LOGGING_LOCK:
        for logger_name in ["tradingagents", "tradingagents.audit"]:
            logger = logging.getLogger(logger_name)
            for handler in list(logger.handlers):
                handler.close()
                logger.removeHandler(handler)
        _LOGGING_INITIALISED = False


def emit_audit_record(record: Dict[str, Any]) -> None:
    """Emit a JSON line to the audit logger."""
    record = dict(record)
    record.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
    logging.getLogger("tradingagents.audit").info(json.dumps(record, default=str))
