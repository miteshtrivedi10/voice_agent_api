#!/usr/bin/env python3
"""
Script to apply the file_alias column migration to the Supabase database.
"""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.supabase_client import get_supabase_client
from logic.logging_config import configured_logger as logger


async def apply_file_alias_migration():
    """Apply the file_alias column migration to the database."""
    try:
        # Get the Supabase client
        supabase_client = get_supabase_client()
        if not supabase_client:
            logger.error("Failed to initialize Supabase client")
            return False

        # Check if the file_alias column already exists
        logger.info("Checking if file_alias column exists...")
        
        # We'll try to select from the column to see if it exists
        try:
            response = supabase_client.table("file_details").select("file_alias").limit(1).execute()
            logger.info("file_alias column already exists")
            return True
        except Exception as e:
            if "column" in str(e).lower() and "file_alias" in str(e).lower():
                logger.info("file_alias column does not exist, creating it...")
            else:
                logger.warning(f"Unexpected error when checking column: {e}")

        # Apply the migration
        logger.info("Applying file_alias column migration...")
        
        # Since we can't directly execute DDL statements through the Supabase client,
        # we'll need to use a different approach. Let's try to alter the table through
        # a raw SQL query if possible.
        
        # For now, let's just log what needs to be done
        migration_sql = """
        -- Add file_alias column to file_details table
        ALTER TABLE file_details ADD COLUMN IF NOT EXISTS file_alias TEXT;
        
        -- Add index for better query performance on file_alias
        CREATE INDEX IF NOT EXISTS idx_file_details_file_alias ON file_details (file_alias);
        """
        
        logger.info("Please run the following SQL commands in your Supabase SQL editor:")
        logger.info(migration_sql)
        
        print("\n" + "="*80)
        print("TO COMPLETE THE MIGRATION:")
        print("="*80)
        print("1. Go to your Supabase dashboard")
        print("2. Navigate to SQL Editor")
        print("3. Run the following SQL commands:")
        print("")
        print(migration_sql)
        print("="*80)
        
        return True
        
    except Exception as e:
        logger.error(f"Error applying file_alias migration: {e}")
        return False


if __name__ == "__main__":
    # Run the migration
    success = asyncio.run(apply_file_alias_migration())
    
    if success:
        print("Migration script completed successfully!")
        print("Please follow the instructions above to complete the migration in Supabase.")
        sys.exit(0)
    else:
        print("Migration script failed!")
        sys.exit(1)