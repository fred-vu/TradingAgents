from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path


def load_audit_module():
    module_path = Path(__file__).resolve().parents[2] / "tradingagents" / "utils" / "audit.py"
    spec = importlib.util.spec_from_file_location("audit_module", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_audit_logger_writes_jsonl(tmp_path):
    audit_module = load_audit_module()
    logger = audit_module.AuditLogger(base_dir=tmp_path)

    record_path = logger.log({"symbol": "NVDA", "trade_date": "2025-05-01"})

    assert record_path.exists()
    contents = record_path.read_text().strip().splitlines()
    assert len(contents) == 1
    assert '"symbol": "NVDA"' in contents[0]
    assert '"trade_id"' in contents[0]


def test_audit_logger_prunes_old_files(tmp_path):
    audit_module = load_audit_module()
    base_dir = tmp_path / "audit"
    base_dir.mkdir()

    old_date = datetime.now(timezone.utc) - timedelta(days=120)
    old_file = base_dir / f"trades_{old_date.strftime('%Y%m%d')}.jsonl"
    old_file.write_text("{}\n", encoding="utf-8")

    logger = audit_module.AuditLogger(base_dir=base_dir, retention_days=90)
    logger.log({"symbol": "AAPL", "trade_date": "2025-05-01"})

    assert not old_file.exists()
