"""Configuration management for the voice agent API."""
import os
from dotenv import load_dotenv
from logic.logging_config import configured_logger as logger
from typing import Optional


class Settings:
    """Settings class to manage environment variables."""
    
    def __init__(self):
        """Initialize settings from environment variables."""
        # Load environment variables from .env file
        load_dotenv(override=True)
        
        # Supabase configuration
        self.SUPABASE_URL: str = os.getenv("SUPABASE_URL", "https://your-project-url.supabase.co")
        self.SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "your-anon-key")
        
        # LiveKit configuration
        self.LIVEKIT_URL: str = os.getenv("LIVEKIT_URL", "ws://localhost:7880")
        self.LIVEKIT_API_KEY: str = os.getenv("LIVEKIT_API_KEY", "your-api-key")
        self.LIVEKIT_API_SECRET: str = os.getenv("LIVEKIT_API_SECRET", "your-api-secret")
        
        # Embedding API configuration
        self.EMBEDDING_API_URL: str = os.getenv("EMBEDDING_API_URL", "http://localhost:8001/generate-embedding")
        
        # Upload directory
        self.UPLOAD_DIRECTORY: str = os.getenv("UPLOAD_DIRECTORY", "uploaded_files")
        
        # Logging configuration
        self.LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
        
        logger.info("Settings loaded successfully")


# Create a global settings instance
settings = Settings()