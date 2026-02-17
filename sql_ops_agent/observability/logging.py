import structlog
import logging
import sys

def configure_logging(log_level: str = "INFO", json_format: bool = True):
    shared_processors = [
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.contextvars.merge_contextvars,
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

    # Configure standard logging to use structlog
    formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer() if json_format else structlog.dev.ConsoleRenderer(),
    )
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    
    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(log_level.upper())
