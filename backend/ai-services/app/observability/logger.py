import logging
import sys
import json
from typing import Any, Dict


REDACTED_KEYS = {
    "authorization",
    "x-internal-service-secret",
    "internal_service_secret",
    "password",
    "token",
    "groq_api_key",
    "qdrant_api_key",
    "incois_api_key",
    "weather_api_key",
    "tide_api_key",
    "geocoder_api_key",
    "embedding_api_key",
    "secret",
    "api_key",
}


def redact_sensitive_data(data: Any) -> Any:
    if isinstance(data, dict):
        sanitized = {}
        for k, v in data.items():
            if str(k).lower() in REDACTED_KEYS:
                sanitized[k] = "[REDACTED]"
            else:
                sanitized[k] = redact_sensitive_data(v)
        return sanitized
    elif isinstance(data, list):
        return [redact_sensitive_data(item) for item in data]
    return data


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_obj: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include structured extra fields
        if hasattr(record, "props"):
            log_obj["props"] = redact_sensitive_data(record.props)

        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_obj)


def setup_logger(name: str = "orca-agent-core") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)

    logger.propagate = False
    return logger


logger = setup_logger()
