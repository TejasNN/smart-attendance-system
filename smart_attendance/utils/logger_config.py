import logging
from logging.handlers import RotatingFileHandler
import os

def setup_scheduler_logger():
    """
    Configures a rotating log file for the auto absentee scheduler.
    Log file: logs/auto_absentee_log.log
    Keeps up to 5 backups, each up to 1 MB.
    """
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
    os.makedirs(logs_dir, exist_ok=True)

    log_file = os.path.join(logs_dir, "auto_absentee_log.log")

    # Create a rotating file handler(1 MB per file, 5 backups)
    file_handler = RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=5)
    file_handler.setLevel(logging.INFO)

    # Set a clear and readable format
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(formatter)

    # Configure the root logger (or return a named logger)
    logger = logging.getLogger("auto_absentee_scheduler")
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.propagate = False

    return logger