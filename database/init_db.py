"""Script to initialize the database."""
import asyncio
from dotenv import load_dotenv
load_dotenv(override=True)  # Load environment variables
from database.migrations import initialize_database


async def main():
    """Initialize the database."""
    success = initialize_database()
    if success:
        print("Database initialized successfully")
    else:
        print("Failed to initialize database")


if __name__ == "__main__":
    asyncio.run(main())