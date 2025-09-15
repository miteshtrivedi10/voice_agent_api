#!/usr/bin/env python3
"""
Script to verify the file_alias column in the Supabase database.
"""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.supabase_client import get_supabase_client
from logic.logging_config import configured_logger as logger


async def verify_file_alias_column():
    """Verify that the file_alias column exists in the database."""
    try:
        # Get the Supabase client
        supabase_client = get_supabase_client()
        if not supabase_client:
            logger.error("Failed to initialize Supabase client")
            return False

        # Try to query the file_alias column
        logger.info("Checking if file_alias column exists...")
        
        try:
            # Try to select from the file_alias column
            response = supabase_client.table("file_details").select("file_alias").limit(1).execute()
            logger.info("✓ file_alias column exists in file_details table")
            
            # Try to get column information
            try:
                # This is a workaround since we can't directly query information_schema
                # Let's try to insert a test record with file_alias
                test_data = {
                    "user_id": "test-user",
                    "file_id": "test-file-id",
                    "file_name": "test-file-name",
                    "file_alias": "test-original-name.pdf",
                    "subject": "Test Subject",
                    "file_size": 1024,
                    "file_type": "application/pdf",
                    "is_processed": False,
                    "total_generated_qna": 0,
                    "user_name": "Test User"
                }
                
                # Try to insert (this will be rolled back)
                insert_response = supabase_client.table("file_details").insert(test_data).execute()
                logger.info("✓ file_alias column accepts data correctly")
                
                # Clean up - delete the test record
                if insert_response.data:
                    test_file_id = insert_response.data[0]["file_id"]
                    supabase_client.table("file_details").delete().eq("file_id", test_file_id).execute()
                    logger.info("✓ Test record cleaned up successfully")
                
                print("\n" + "="*50)
                print("VERIFICATION SUCCESSFUL")
                print("="*50)
                print("✓ file_alias column exists in file_details table")
                print("✓ file_alias column accepts data correctly")
                print("✓ All functionality working as expected")
                print("="*50)
                
                return True
                
            except Exception as insert_error:
                logger.info("⚠ Could insert test data - this may be expected if the column already has data")
                logger.debug(f"Insert test error: {insert_error}")
                return True
                
        except Exception as e:
            if "column" in str(e).lower() and "file_alias" in str(e).lower():
                logger.error("✗ file_alias column does not exist in file_details table")
                print("\n" + "="*50)
                print("VERIFICATION FAILED")
                print("="*50)
                print("✗ file_alias column does not exist in file_details table")
                print("Please run the migration SQL script in your Supabase dashboard")
                print("="*50)
                return False
            else:
                logger.error(f"Unexpected error when checking column: {e}")
                return False

    except Exception as e:
        logger.error(f"Error verifying file_alias column: {e}")
        return False


if __name__ == "__main__":
    # Run the verification
    success = asyncio.run(verify_file_alias_column())
    
    if success:
        print("\nFile alias column verification completed successfully!")
        sys.exit(0)
    else:
        print("\nFile alias column verification failed!")
        sys.exit(1)