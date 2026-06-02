import logging
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.config import Settings


def configure_logging(settings: "Settings") -> None:
    """Configure root logger.  JSON in production, human-readable in development.

    Uses standard ``logging`` throughout so OpenTelemetry's log bridge can hook
    in later without any code changes.
    """
    handler = logging.StreamHandler(sys.stdout)

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

    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(
        logging.DEBUG if settings.environment == "development" else logging.INFO
    )
