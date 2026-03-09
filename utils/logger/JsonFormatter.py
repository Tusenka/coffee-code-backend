from datetime import datetime, UTC
import json
from logging import Formatter


class JsonFormatter(Formatter):
    def format(self, record) -> str:
        log_record = {
            "time": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "path": f"{record.pathname}:{record.lineno}",
            "message": record.getMessage(),
        }

        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record, ensure_ascii=False)
