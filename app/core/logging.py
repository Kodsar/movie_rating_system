import logging
import sys


def setup_logger() -> logging.Logger:
    """
    Configure application-wide logger.
    Logs are written to stdout so Docker can capture them.
    """
    logger = logging.getLogger("movie-rating")
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(name)s - %(message)s"
    )
    handler.setFormatter(formatter)

    # Prevent duplicate logs
    if not logger.handlers:
        logger.addHandler(handler)

    return logger
