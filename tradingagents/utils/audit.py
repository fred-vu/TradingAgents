import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, Optional


logger = logging.getLogger("tradingagents.audit")


@dataclass
class AuditLogger:
    base_dir: Path
    retention_days: int = 90
    file_prefix: str = "trades"

    def __post_init__(self) -> None:
        self.base_dir = Path(self.base_dir).expanduser()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._prune_old_logs()

    def _file_for_date(self, dt: datetime) -> Path:
        return self.base_dir / f"{self.file_prefix}_{dt.strftime('%Y%m%d')}.jsonl"

    def _prune_old_logs(self) -> None:
        if self.retention_days <= 0:
            return
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.retention_days)
        for path in self.base_dir.glob(f"{self.file_prefix}_*.jsonl"):
            try:
                date_part = path.stem.split("_")[-1]
                log_date = datetime.strptime(date_part, "%Y%m%d").replace(tzinfo=timezone.utc)
            except ValueError:
                continue
            if log_date < cutoff:
                try:
                    path.unlink(missing_ok=True)
                except Exception:
                    logger.warning("Failed to remove old audit log %s", path, exc_info=True)

    def _prepare_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        prepared = dict(record)
        prepared.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
        prepared.setdefault("trade_id", uuid.uuid4().hex)
        prepared.setdefault("execution_status", "PENDING")
        prepared.setdefault("errors", [])
        return prepared

    def log(self, record: Dict[str, Any]) -> Path:
        prepared = self._prepare_record(record)
        timestamp = datetime.fromisoformat(prepared["timestamp"])
        file_path = self._file_for_date(timestamp)
        line = json.dumps(prepared, default=str)
        with file_path.open("a", encoding="utf-8") as fh:
            fh.write(line)
            fh.write("\n")

        logging.getLogger("tradingagents.audit").info(line)
        return file_path
