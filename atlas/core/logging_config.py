"""Centralized logging configuration for ATLAS."""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
    format_style: str = "standard",
) -> logging.Logger:
    """Configure logging for ATLAS.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional path to log file
        format_style: 'standard', 'detailed', or 'minimal'

    Returns:
        Root ATLAS logger
    """
    # Format strings
    formats = {
        "standard": "[%(asctime)s] %(levelname)s %(name)s: %(message)s",
        "detailed": "[%(asctime)s] %(levelname)s %(name)s (%(filename)s:%(lineno)d): %(message)s",
        "minimal": "%(levelname)s: %(message)s",
    }

    log_format = formats.get(format_style, formats["standard"])
    date_format = "%Y-%m-%d %H:%M:%S"

    # Create formatter
    formatter = logging.Formatter(log_format, datefmt=date_format)

    # Get root ATLAS logger
    logger = logging.getLogger("atlas")
    logger.setLevel(level)

    # Clear existing handlers
    logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific ATLAS module.

    Args:
        name: Module name (e.g., 'agents', 'routing', 'web')

    Returns:
        Logger instance
    """
    return logging.getLogger(f"atlas.{name}")


# Module-level loggers for common components
agents_logger = get_logger("agents")
routing_logger = get_logger("routing")
web_logger = get_logger("web")
core_logger = get_logger("core")
monitoring_logger = get_logger("monitoring")


# Initialize default logging on import
_default_logger = setup_logging()
