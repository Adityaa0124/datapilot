"""
Logging Initialization Module

Configures application logging, including structured formatting, request ID injection,
and console/file rotation outputs.
Includes automated fallback to Python standard library `logging` when `loguru` is unavailable.
"""

import sys
from pathlib import Path

try:
    from loguru import logger
    from app.conf.app_config import app_config
    from app.core.context import request_id_ctx_var

    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<magenta>request_id - {extra[request_id]}</magenta> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )

    def inject_request_id(record):
        """Injects request_id from context into the log record's extra dictionary."""
        request_id = request_id_ctx_var.get()
        record["extra"]["request_id"] = request_id

    logger.remove()
    logger = logger.patch(inject_request_id)

    if app_config.logging.console.enable:
        logger.add(
            sink=sys.stdout,
            level=app_config.logging.console.level,
            format=log_format,
        )

    if app_config.logging.file.enable:
        path = Path(app_config.logging.file.path)
        path.mkdir(parents=True, exist_ok=True)
        logger.add(
            sink=path / "app.log",
            level=app_config.logging.file.level,
            format=log_format,
            rotation=app_config.logging.file.rotation,
            retention=app_config.logging.file.retention,
        )

except ImportError:
    import logging

    logger = logging.getLogger("datapilot")
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
