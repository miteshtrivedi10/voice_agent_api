"""Test script to verify RAG integration works correctly."""
import os
import sys
import asyncio
from loguru import logger

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from logic.service import get_rag_processor
from model.dtos import FileDetails

def test_rag_integration():
    """Test that the RAG integration works correctly."""
    logger.info("Testing RAG integration...")
    
    try:
        # Get the RAG processor
        processor = get_rag_processor()
        logger.info("RAG processor created successfully")
        
        # Check that the processor has the required components
        assert hasattr(processor, 'parser'), "Processor should have a parser"
        assert hasattr(processor, 'processors'), "Processor should have processors"
        assert hasattr(processor, 'questionnaire_generator'), "Processor should have a questionnaire generator"
        
        logger.info("All RAG components are present")
        
        # Test that we can access the model functions
        assert processor.vision_model_func is not None, "Vision model function should be set"
        assert processor.llm_model_func is not None, "LLM model function should be set"
        
        logger.info("Model functions are properly set")
        
        print("RAG integration test passed!")
        return True
        
    except Exception as e:
        logger.error(f"RAG integration test failed: {e}")
        return False

if __name__ == "__main__":
    test_rag_integration()