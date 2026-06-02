import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.config import Settings


def configure_logging(settings: "Settings") -> None:
    """Configure root logger.  JSON in production, human-readable in development.

    A StreamHandler (stdout) is always added.  When ``settings.log_file`` is set
    a RotatingFileHandler is added alongside it, rotating at ``log_max_bytes``
    and keeping ``log_backup_count`` backups.

    Uses standard ``logging`` throughout so OpenTelemetry's log bridge can hook
    in later without any code changes.
    """
    if settings.environment == "production":
        try:
            from pythonjsonlogger import jsonlogger

            formatter = jsonlogger.JsonFormatter(
                "%(asctime)s %(name)s %(levelname)s %(message)s"
            )
        except ImportError:  # pragma: no cover
            formatter = logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            )
    else:
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]

    if settings.log_file:
        log_path = Path(settings.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=settings.log_max_bytes,
            backupCount=settings.log_backup_count,
            encoding="utf-8",
        )
        handlers.append(file_handler)

    for handler in handlers:
        handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    for handler in handlers:
        root.addHandler(handler)
    root.setLevel(
        logging.DEBUG if settings.environment == "development" else logging.INFO
    )
