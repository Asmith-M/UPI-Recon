"""
Centralized Logging Configuration using Loguru
Provides structured JSON logging with rotation and filtering
"""

import os
import sys
from loguru import logger
from config import OUTPUT_DIR


def setup_logging(log_level: str = "INFO", enable_json: bool = True):
    """
    Configure Loguru logging with structured JSON format and file rotation

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_json: Enable JSON format for structured logging
    """
    # Remove default handler
    logger.remove()

    # Define log format
    if enable_json:
        # Structured JSON format for production
        log_format = (
            "{"
            '"timestamp": "{time:YYYY-MM-DD HH:mm:ss.SSS}", '
            '"level": "{level}", '
            '"logger": "{name}", '
            '"message": "{message}", '
            '"module": "{module}", '
            '"function": "{function}", '
            '"line": {line}, '
            '"extra": {extra}'
            "}"
        )
    else:
        # Human-readable format for development
        log_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )

    # Console handler
    logger.add(
        sys.stdout,
        format=log_format,
        level=log_level,
        colorize=not enable_json,
        serialize=enable_json
    )

    # File handler with rotation
    log_dir = os.path.join(OUTPUT_DIR, "logs")
    os.makedirs(log_dir, exist_ok=True)

    # Main application log
    logger.add(
        os.path.join(log_dir, "app_{time:YYYY-MM-DD}.log"),
        format=log_format,
        level=log_level,
        rotation="00:00",  # Rotate at midnight
        retention="30 days",  # Keep logs for 30 days
        compression="gz",  # Compress old logs
        serialize=enable_json,
        encoding="utf-8"
    )

    # Error log (WARNING and above)
    logger.add(
        os.path.join(log_dir, "error_{time:YYYY-MM-DD}.log"),
        format=log_format,
        level="WARNING",
        rotation="00:00",
        retention="90 days",
        compression="gz",
        serialize=enable_json,
        encoding="utf-8",
        filter=lambda record: record["level"].no >= 30  # WARNING and above
    )

    # Audit log (separate from application logs)
    logger.add(
        os.path.join(log_dir, "audit_{time:YYYY-MM-DD}.log"),
        format=log_format,
        level="INFO",
        rotation="00:00",
        retention="365 days",  # Keep audit logs for 1 year
        compression="gz",
        serialize=enable_json,
        encoding="utf-8",
        filter=lambda record: "audit" in record["extra"] or record["name"] == "audit_trail"
    )

    # Set log level for third-party libraries
    import logging
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)
    logging.getLogger("pandas").setLevel(logging.WARNING)

    logger.info("Logging configuration initialized", extra={"log_level": log_level, "json_format": enable_json})


def get_logger(name: str):
    """
    Get a logger instance with the specified name

    Args:
        name: Logger name (usually __name__)

    Returns:
        Loguru logger instance
    """
    return logger.bind(name=name)


# Global logger instance
app_logger = get_logger("reconciliation_app")
