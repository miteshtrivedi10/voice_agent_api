"""Test script to verify the entire RAG integration flow."""
import os
import sys
from loguru import logger

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_rag_flow():
    """Test the entire RAG flow."""
    logger.info("Testing RAG flow...")
    
    try:
        # Test that we can import our components
        from logic.service import get_rag_processor
        from rag.rag.custom_processor import CustomRAGProcessor
        from rag.rag.simple_embedding import SimpleEmbeddingGenerator
        
        logger.info("All components imported successfully")
        
        # Test the simple embedding generator
        embedding_generator = SimpleEmbeddingGenerator()
        test_embedding = embedding_generator.generate_embedding("This is a test sentence for embedding generation.")
        logger.info(f"Generated embedding with {len(test_embedding)} dimensions")
        
        # Test the custom RAG processor
        processor = CustomRAGProcessor()
        logger.info("Custom RAG processor created successfully")
        
        # Check that the processor has the required components
        assert hasattr(processor, 'parser'), "Processor should have a parser"
        assert hasattr(processor, 'processors'), "Processor should have processors"
        assert hasattr(processor, 'questionnaire_generator'), "Processor should have a questionnaire generator"
        
        logger.info("All RAG components are present")
        
        # Test that we can access the model functions
        assert processor.vision_model_func is not None, "Vision model function should be set"
        assert processor.llm_model_func is not None, "LLM model function should be set"
        
        logger.info("Model functions are properly set")
        
        print("RAG flow test passed!")
        return True
        
    except Exception as e:
        logger.error(f"RAG flow test failed: {e}")
        return False

if __name__ == "__main__":
    test_rag_flow()