import logging
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

logger = logging.getLogger(__name__)


def load_config(config_path: str = "config/default.yaml") -> Dict[str, Any]:
    """Loads a YAML configuration file.

    Args:
        config_path: The path to the YAML configuration file. Defaults to "config/default.yaml".

    Returns:
        A dictionary containing the configuration data. Returns an empty dictionary
        if the file is not found or fails to load.
    """
    path = Path(config_path)
    if not path.exists():
        logger.warning(f"Config file not found at: {config_path}. Proceeding with default/empty configuration.")
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
            logger.debug(f"Successfully loaded configuration from {config_path}")
            return config
    except Exception as e:
        logger.error(f"Critical error loading configuration from {config_path}: {e}")
        return {}


def setup_logging(level: str = "INFO", log_file: str = "recon.log") -> None:
    """Configures the global logging system for the application.

    Sets up both a file handler for persistent logging and a stream handler
    for real-time console output. Standardizes the log format across the project.

    Args:
        level: The logging level to set (e.g., "DEBUG", "INFO", "WARNING"). Defaults to "INFO".
        log_file: The name of the file where logs will be saved. Defaults to "recon.log".
    """
    root = logging.getLogger()
    log_level = getattr(logging, level.upper(), logging.INFO)
    root.setLevel(log_level)

    # Clear existing handlers to prevent duplicate log entries
    if root.handlers:
        for handler in root.handlers[:]:
            root.removeHandler(handler)

    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    formatter = logging.Formatter(log_format)

    # Prepare file handler
    try:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    except Exception as e:
        # Fallback to local logger if file handler fails (common on Windows with locked files)
        logger.warning(f"Could not initialize FileHandler for {log_file}: {e}")

    # Prepare console handler
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    root.addHandler(stream_handler)

    logger.info(f"Logging initialized | Level: {level.upper()} | Output: {log_file}")
