import logging
import importlib.util
from pathlib import Path


def load_logging_utils():
    module_path = Path(__file__).resolve().parents[2] / "tradingagents" / "logging_utils.py"
    spec = importlib.util.spec_from_file_location("logging_utils_module", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_init_logging_creates_files(tmp_path):
    logging_utils = load_logging_utils()
    logging_utils.reset_logging_for_tests()

    config = {
        "log_dir": str(tmp_path / "logs"),
        "log_level": "INFO",
        "audit_log_filename": "audit.jsonl",
    }

    logging_utils.init_logging(config)

    logger = logging.getLogger("tradingagents")
    logger.info("hello world")
    logging_utils.emit_audit_record({"event": "trade", "decision": "BUY"})

    log_file = tmp_path / "logs" / "tradingagents.log"
    audit_file = tmp_path / "logs" / "audit.jsonl"

    assert log_file.exists()
    assert audit_file.exists()

    assert "hello world" in log_file.read_text()
    assert '"decision": "BUY"' in audit_file.read_text()


def test_init_logging_idempotent(tmp_path):
    logging_utils = load_logging_utils()
    logging_utils.reset_logging_for_tests()

    config = {
        "log_dir": str(tmp_path / "logs"),
        "log_level": "DEBUG",
    }

    logging_utils.init_logging(config)
    handler_count_first = len(logging.getLogger("tradingagents").handlers)
    logging_utils.init_logging(config)
    handler_count_second = len(logging.getLogger("tradingagents").handlers)

    assert handler_count_first == handler_count_second

