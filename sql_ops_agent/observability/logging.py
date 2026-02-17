import structlog
import logging
import sys
import contextvars
from typing import Any, Dict

# ContextVar to store request ID
request_id_var = contextvars.ContextVar("request_id", default="unknown")

def add_request_id(logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Structlog processor that adds the request_id from contextvars.
    """
    event_dict["request_id"] = request_id_var.get()
    return event_dict

def configure_logging(log_level: str = "INFO", json_format: bool = True):
    shared_processors = [
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        add_request_id, # Add our custom processor
        structlog.contextvars.merge_contextvars,
        structlog.processors.CallsiteParameterAdder(
            {
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.FUNC_NAME,
                structlog.processors.CallsiteParameter.LINENO,
            }
        ),
    ]

    if json_format:
        processors = shared_processors + [
            structlog.processors.JSONRenderer()
        ]
    else:
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer()
        ]

    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer() if json_format else structlog.dev.ConsoleRenderer(),
    )
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    
    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(log_level.upper())
