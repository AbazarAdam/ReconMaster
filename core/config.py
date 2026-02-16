import yaml
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

def load_config(config_path: str = "config/default.yaml") -> Dict[str, Any]:
    """Loads a YAML configuration file."""
    path = Path(config_path)
    if not path.exists():
        logger.warning(f"Config file {config_path} not found. Using empty config.")
        return {}

    try:
        with open(path, "r") as f:
            config = yaml.safe_load(f) or {}
            return config
    except Exception as e:
        logger.error(f"Failed to load config {config_path}: {e}")
        return {}

def setup_logging(level: str = "INFO", log_file: str = "recon.log"):
    """Configures the logging system."""
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # Clear existing handlers to avoid duplicates
    if root.handlers:
        for handler in root.handlers[:]:
            root.removeHandler(handler)
            
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    
    try:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    except Exception:
        # Silently fail if file is locked, at least show in stream
        pass
        
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    root.addHandler(stream_handler)
    
    logger.info(f"Logging initialized. Level: {level}, File: {log_file}")
