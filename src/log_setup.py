"""
Centralized logging configuration for all scorecard scripts.

Creates timestamped log files in the logs/ directory at the project root.
Each run gets its own log file. Console output is preserved alongside file logging.

Usage:
    from log_setup import get_run_logger
    logger, log_path = get_run_logger("single_llm")
    logger.info("Starting run...")
"""
import os
import sys
import logging
import datetime
from pathlib import Path
from typing import Tuple

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR = _PROJECT_ROOT / "logs"


def get_run_logger(
    script_name: str,
    level: int = logging.INFO,
) -> Tuple[logging.Logger, Path]:
    """Create a logger that writes to both console and a timestamped log file.

    Args:
        script_name: Name used for the log file (e.g. "single_llm", "run_all").
        level: Logging level (default INFO).

    Returns:
        (logger, log_file_path) tuple.
    """
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"{script_name}_{timestamp}.log"
    log_path = LOGS_DIR / log_filename

    logger = logging.getLogger(f"scorecard.{script_name}")
    logger.setLevel(level)

    # Avoid duplicate handlers if called multiple times
    if logger.handlers:
        return logger, log_path

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler — captures everything
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(level)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # Console handler — same level
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(level)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger, log_path


class TeeWriter:
    """Redirect stdout/stderr to both console and a log file.

    Use this to capture print() output from scripts that don't use logging.
    """

    def __init__(self, log_path: Path, original_stream):
        self.log_file = open(log_path, "a", encoding="utf-8")
        self.original = original_stream

    def write(self, text):
        self.original.write(text)
        self.log_file.write(text)
        self.log_file.flush()

    def flush(self):
        self.original.flush()
        self.log_file.flush()

    def close(self):
        self.log_file.close()
