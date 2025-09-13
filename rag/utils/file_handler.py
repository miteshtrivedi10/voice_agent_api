import os
import logging
from typing import List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class FileHandler:
    @staticmethod
    def validate_file_path(file_path: str) -> bool:
        """Validate if the file path exists and is accessible."""
        try:
            path = Path(file_path)
            return path.exists() and path.is_file()
        except Exception as e:
            logger.error(f"Error validating file path {file_path}: {e}")
            return False
    
    @staticmethod
    def get_file_extension(file_path: str) -> str:
        """Get the file extension."""
        return Path(file_path).suffix.lower()
    
    @staticmethod
    def is_supported_format(file_path: str) -> bool:
        """Check if the file format is supported."""
        supported_extensions = {'.pdf', '.png', '.jpg', '.jpeg'}
        return FileHandler.get_file_extension(file_path) in supported_extensions
    
    @staticmethod
    def validate_directory(directory_path: str) -> bool:
        """Validate if the directory exists and is accessible."""
        try:
            path = Path(directory_path)
            return path.exists() and path.is_dir()
        except Exception as e:
            logger.error(f"Error validating directory path {directory_path}: {e}")
            return False
    
    @staticmethod
    def create_directory(directory_path: str) -> bool:
        """Create directory if it doesn't exist."""
        try:
            Path(directory_path).mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"Error creating directory {directory_path}: {e}")
            return False
