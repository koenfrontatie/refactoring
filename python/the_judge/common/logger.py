import logging
import warnings
import sys
from typing import Optional

def setup_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    warnings.filterwarnings(
        "ignore",
        category=FutureWarning
    )

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    
    log_level = getattr(logging, level or "INFO")
    logger.setLevel(log_level)
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger
