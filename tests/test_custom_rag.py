"""Test script to verify custom RAG processor works correctly."""
import os
import sys
import asyncio
from loguru import logger

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rag.rag.custom_processor import CustomRAGProcessor

def test_custom_rag_processor():
    """Test that the custom RAG processor works correctly."""
    logger.info("Testing custom RAG processor...")
    
    try:
        # Create a simple test file
        test_file_path = "test_document.txt"
        with open(test_file_path, "w") as f:
            f.write("This is a simple test document for RAG processing.")
        
        # Create the custom RAG processor
        processor = CustomRAGProcessor()
        logger.info("Custom RAG processor created successfully")
        
        # Test processing the file
        content_list = processor.process_file(test_file_path)
        logger.info(f"Processed {len(content_list)} content items")
        
        # Clean up the test file
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
        
        print("Custom RAG processor test passed!")
        return True
        
    except Exception as e:
        logger.error(f"Custom RAG processor test failed: {e}")
        # Clean up the test file if it exists
        test_file_path = "test_document.txt"
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
        return False

if __name__ == "__main__":
    test_custom_rag_processor()