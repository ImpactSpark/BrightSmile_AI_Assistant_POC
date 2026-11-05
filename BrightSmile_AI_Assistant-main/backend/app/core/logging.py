import logging
import sys

from app.core.config import settings


def configure_logging() -> None:
    """Structured, PHI-safe logging.

    Never pass raw image bytes, file contents, or patient identifiers to
    these loggers. Only case_id (a generated opaque id), timings, and
    condition/confidence summaries are safe to log.
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt='{"ts":"%(asctime)s","level":"%(levelname)s",'
            '"logger":"%(name)s","msg":%(message)r}'
        )
    )
    root = logging.getLogger()
    root.setLevel(settings.log_level)
    root.handlers = [handler]


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
