# app/logging_config.py
import logging
import structlog
from typing import Union
import sys


def setup_logging(log_level: Union[int, str] = logging.INFO):
    """Set up structured logging for the application.

    This configures structlog and applies it to the root logger,
    ensuring all logs use the same format and level filtering.
    """
    # Convert string log level to integer if needed
    if isinstance(log_level, str):
        log_level = getattr(logging, log_level.upper())

    # --- Structlog configuration ---
    shared_processors = [
        # Add context from contextvars
        structlog.contextvars.merge_contextvars,
        # Add log level name
        structlog.stdlib.add_log_level,
        # Add logger name
        structlog.stdlib.add_logger_name,
        # Format any exc_info
        structlog.processors.format_exc_info,
        # Add timestamp
        structlog.processors.TimeStamper("iso"),
    ]

    structlog.configure(
        processors=shared_processors + [structlog.dev.ConsoleRenderer(colors=True)],
        logger_factory=structlog.stdlib.LoggerFactory(),
        # Filter logs according to level *before* processing
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        cache_logger_on_first_use=True,
    )

    # --- Standard library logging integration ---

    # Add custom filter to prevent duplicate logs due to reloader
    class DuplicateFilter(logging.Filter):
        def __init__(self):
            self.logged = set()

        def filter(self, record):
            # Create a unique key for the log message
            log_key = (record.name, record.levelno, record.msg)
            if log_key in self.logged:
                return False
            self.logged.add(log_key)
            return True

    # Create a formatter using structlog processors
    formatter = structlog.stdlib.ProcessorFormatter(
        # Use ConsoleRenderer for the final output
        processor=structlog.dev.ConsoleRenderer(colors=True),
        # Processors to apply to logs from non-structlog loggers
        foreign_pre_chain=shared_processors,
    )

    # Create a handler using this formatter
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.setLevel(log_level)  # Ensure handler respects level
    handler.addFilter(DuplicateFilter())  # Add the duplicate filter

    # Configure the root logger
    root_logger = logging.getLogger()
    # Clear any existing handlers
    root_logger.handlers = []
    # Add our single structlog handler
    root_logger.addHandler(handler)
    # Set the root logger level
    root_logger.setLevel(log_level)

    # Ensure other loggers propagate to root
    for name in logging.root.manager.loggerDict:
        if name != "root":  # Don't reset root again
            logging.getLogger(name).handlers = []
            logging.getLogger(name).propagate = True
            logging.getLogger(name).setLevel(log_level)  # Ensure they respect level too

    # Set specific loggers to DEBUG for tool call tracing
    # Only set these to DEBUG if overall level is INFO or higher
    if isinstance(log_level, int) and log_level > logging.DEBUG:
        # Set debug level for critical tool call components
        logging.getLogger("app.routes.chat_completions").setLevel(logging.DEBUG)
        logging.getLogger("app.services.function_calling").setLevel(logging.DEBUG)
        logging.getLogger("app.services.tools.registry").setLevel(logging.DEBUG)
        logger = logging.getLogger(__name__)
        logger.debug("Enabled DEBUG logging for tool call components")

    return None  # setup_logging doesn't return a config dict


def get_uvicorn_log_config(log_level: Union[int, str] = logging.INFO):
    """Get a logging config for Uvicorn that disables its default handlers
    and makes it propagate to the root logger.
    """
    if isinstance(log_level, str):
        log_level_int = getattr(logging, log_level.upper())
    else:
        log_level_int = log_level
    log_level_name = logging.getLevelName(log_level_int)

    return {
        "version": 1,
        "disable_existing_loggers": False,  # Don't disable loggers
        "formatters": {},
        "handlers": {
            "null": {  # Define a null handler to effectively disable default output
                "class": "logging.NullHandler",
            },
        },
        "loggers": {
            # Route Uvicorn logs to the root logger
            "uvicorn": {
                "handlers": ["null"],  # Use null handler to prevent default output
                "level": log_level_name,
                "propagate": True,  # Propagate to root logger
            },
            "uvicorn.error": {
                "handlers": ["null"],
                "level": log_level_name,
                "propagate": True,
            },
            "uvicorn.access": {
                "handlers": ["null"],
                "level": log_level_name,
                "propagate": True,
            },
        },
    }


# We'll get the actual config at runtime
LOGGING_CONFIG = None
