"""Supabase client configuration and initialization."""

from supabase import create_client, Client
from loguru import logger

# Import settings
from logic.config import settings


class SupabaseClientManager:
    """Manages the Supabase client instance."""
    
    def __init__(self):
        self._client = None
    
    def get_client(self) -> Client | None:
        """Get or create the Supabase client instance."""
        if self._client is None:
            # Supabase configuration from settings
            SUPABASE_URL = settings.SUPABASE_URL
            SUPABASE_KEY = settings.SUPABASE_KEY
            
            # Check if we have valid configuration
            if SUPABASE_URL == "https://your-project-url.supabase.co" or SUPABASE_KEY == "your-anon-key":
                logger.warning("Using default Supabase configuration. Please check your environment variables.")
            else:
                logger.info("Supabase configuration loaded successfully")
            
            try:
                self._client = create_client(SUPABASE_URL, SUPABASE_KEY)
                logger.info("Supabase client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}")
                self._client = None
        
        return self._client


# Create a singleton instance
supabase_manager = SupabaseClientManager()


def get_supabase_client() -> Client | None:
    """Get the Supabase client instance."""
    return supabase_manager.get_client()