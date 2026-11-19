"""
AutoTube AI - Unified Logging Service
Logs to both file and SQLite database for real-time dashboard observability
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
from core.config import config
from database.db import log_event

# Configure standard Python logger
log_file = config.logs_dir / "autotube.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    handlers=[
        logging.FileHandler(str(log_file), encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

_logger = logging.getLogger("AutoTubeAI")


def log_info(module: str, message: str, details: Optional[str] = None):
    _logger.info(f"[{module}] {message}")
    log_event("INFO", module, message, details)


def log_warning(module: str, message: str, details: Optional[str] = None):
    _logger.warning(f"[{module}] {message}")
    log_event("WARNING", module, message, details)


def log_error(module: str, message: str, details: Optional[str] = None):
    _logger.error(f"[{module}] {message} - Details: {details or ''}")
    log_event("ERROR", module, message, details)


def log_success(module: str, message: str, details: Optional[str] = None):
    _logger.info(f"[SUCCESS] [{module}] {message}")
    log_event("SUCCESS", module, message, details)
