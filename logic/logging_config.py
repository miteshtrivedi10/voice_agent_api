"""Centralized logging configuration using loguru."""

import os
import sys
from loguru import logger
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Remove default logger handlers
logger.remove()

# Get log level from environment variable, default to INFO
log_level = os.getenv("LOG_LEVEL", "INFO").upper()

# Add stdout handler with configured level
logger.add(
    sys.stdout,
    level=log_level,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    colorize=True,
)

# Optionally add file handler
log_to_file = os.getenv("LOG_TO_FILE", "false").lower() == "true"
if log_to_file:
    log_file_path = os.getenv("LOG_FILE_PATH", "logs/app.log")
    log_file_rotation = os.getenv("LOG_FILE_ROTATION", "100 MB")
    log_file_retention = os.getenv("LOG_FILE_RETENTION", "7 days")
    
    logger.add(
        log_file_path,
        level=log_level,
        rotation=log_file_rotation,
        retention=log_file_retention,
        compression="zip",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    )

def get_logger(name: str = None):
    """
    Get a configured logger instance.
    
    Args:
        name (str): Optional name for the logger (for context)
        
    Returns:
        loguru.logger: Configured logger instance
    """
    return logger

# Export the configured logger
configured_logger = get_logger()