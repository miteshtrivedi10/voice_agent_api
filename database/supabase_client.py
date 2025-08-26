"""Supabase client configuration and initialization."""

import os
from supabase import create_client, Client
from loguru import logger

# Global variable to hold the Supabase client instance
_supabase_client = None

def get_supabase_client() -> Client:
    """Lazy initialization of Supabase client."""
    global _supabase_client
    
    if _supabase_client is None:
        # Supabase configuration
        SUPABASE_URL = os.getenv("SUPABASE_URL", "https://your-project-url.supabase.co")
        SUPABASE_KEY = os.getenv("SUPABASE_KEY", "your-anon-key")
        
        # Check if we have valid configuration
        if SUPABASE_URL == "https://your-project-url.supabase.co" or SUPABASE_KEY == "your-anon-key":
            logger.warning("Using default Supabase configuration. Please check your environment variables.")
        
        try:
            _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
            logger.info("Supabase client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            _supabase_client = None
    
    return _supabase_client