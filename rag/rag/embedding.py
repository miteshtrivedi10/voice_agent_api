from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
import logging
import numpy as np

logger = logging.getLogger(__name__)


class BaseEmbeddingGenerator(ABC):
    """Base class for embedding generators."""
    
    def __init__(self, model_name: Optional[str] = None, min_dimensions: int = 1024):
        """
        Initialize the base embedding generator.
        
        Args:
            model_name: Name of the model to use for embedding generation
            min_dimensions: Minimum number of dimensions for embeddings
        """
        self.model_name = model_name
        self.min_dimensions = min_dimensions
    
    @abstractmethod
    def generate_embedding(self, content: Union[str, bytes], content_type: str = "text") -> np.ndarray:
        """
        Generate an embedding for the given content.
        
        Args:
            content: Content to generate embedding for (text or image bytes)
            content_type: Type of content ("text" or "image")
            
        Returns:
            Embedding as a numpy array
        """
        pass
    
    @abstractmethod
    def generate_embeddings(self, contents: List[Union[str, bytes]], content_types: Optional[List[str]] = None) -> List[np.ndarray]:
        """
        Generate embeddings for multiple contents.
        
        Args:
            contents: List of contents to generate embeddings for
            content_types: List of content types ("text" or "image")
            
        Returns:
            List of embeddings as numpy arrays
        """
        pass
    
    def validate_embedding(self, embedding: np.ndarray) -> bool:
        """
        Validate that an embedding meets quality requirements.
        
        Args:
            embedding: Embedding to validate
            
        Returns:
            True if embedding is valid, False otherwise
        """
        # Check if embedding is not None
        if embedding is None:
            return False
            
        # Check if embedding is a numpy array
        if not isinstance(embedding, np.ndarray):
            return False
            
        # Check if embedding has the minimum required dimensions
        if embedding.shape[0] < self.min_dimensions:
            logger.warning(f"Embedding has {embedding.shape[0]} dimensions, less than minimum {self.min_dimensions}")
            return False
            
        # Check for NaN or infinite values
        if not np.isfinite(embedding).all():
            logger.warning("Embedding contains NaN or infinite values")
            return False
            
        # Check if embedding is all zeros (no information)
        if np.allclose(embedding, 0):
            logger.warning("Embedding is all zeros")
            return False
            
        return True
    
    def filter_embeddings(self, embeddings: List[np.ndarray], contents: Optional[List[Union[str, bytes]]] = None) -> List[np.ndarray]:
        """
        Filter out low-quality embeddings.
        
        Args:
            embeddings: List of embeddings to filter
            contents: Optional list of contents for logging purposes
            
        Returns:
            List of valid embeddings
        """
        valid_embeddings = []
        
        for i, embedding in enumerate(embeddings):
            if self.validate_embedding(embedding):
                valid_embeddings.append(embedding)
            else:
                content_info = f" (content {i})" if contents is None else f" (content: {contents[i][:50]}...)" if i < len(contents) else f" (content {i})"
                logger.warning(f"Filtering out low-quality embedding{content_info}")
                
        return valid_embeddings