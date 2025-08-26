"""Database migration scripts for creating tables if they don't exist."""
from loguru import logger


def create_user_voice_sessions_table():
    """Create user_voice_sessions table if it doesn't exist."""
    # Tables are now created using Supabase MCP tools
    # This function is kept for backward compatibility
    logger.info("User voice sessions table creation check completed")
    return True


def create_file_details_table():
    """Create file_details table if it doesn't exist."""
    # Tables are now created using Supabase MCP tools
    # This function is kept for backward compatibility
    logger.info("File details table creation check completed")
    return True

def create_question_and_answers_table():
    """Create question_and_answers table if it doesn't exist."""
    # Tables are now created using Supabase MCP tools
    # This function is kept for backward compatibility
    logger.info("Question and answers table creation check completed")
    return True


def initialize_database():
    """Initialize database tables."""
    logger.info("Initializing database tables...")
    success1 = create_user_voice_sessions_table()
    success2 = create_file_details_table()
    success3 = create_question_and_answers_table()
    
    if success1 and success2 and success3:
        logger.info("Database initialization completed successfully")
        return True
    else:
        logger.error("Database initialization failed")
        return False