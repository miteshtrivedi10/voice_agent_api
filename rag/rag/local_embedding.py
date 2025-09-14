import numpy as np
from typing import List, Optional, Union
from sentence_transformers import SentenceTransformer
import hashlib
from logic.logging_config import configured_logger as logger

class LocalEmbeddingGenerator:
    """Local embedding generator using sentence-transformers as reliable fallback."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", min_dimensions: int = 384):
        """
        Initialize local embedding generator.
        
        Args:
            model_name: Sentence-transformers model name
            min_dimensions: Target embedding dimensions (model will be resized if needed)
        """
        try:
            self.model = SentenceTransformer(model_name)
            self.original_dim = self.model.get_sentence_embedding_dimension()
            self.min_dimensions = min_dimensions
            
            logger.info(f"LocalEmbeddingGenerator initialized with model '{model_name}' (dim: {self.original_dim})")
            logger.info(f"Target dimensions set to {min_dimensions}")
            
        except Exception as e:
            logger.error(f"Failed to load sentence-transformers model '{model_name}': {e}")
            logger.warning("Local embeddings will use hash-based fallback")
            self.model = None
            self.original_dim = 0
    
    def generate_embedding(self, content: Union[str, bytes], content_type: str = "text") -> np.ndarray:
        """
        Generate embedding for content using local model.
        
        Args:
            content: Text content to embed
            content_type: Content type (ignored for local embeddings)
            
        Returns:
            Embedding vector as numpy array
        """
        if isinstance(content, bytes):
            try:
                content = content.decode('utf-8')
            except UnicodeDecodeError:
                # For non-text content, use filename or type description
                content = f"Non-text content of type {content_type}"
        
        text = str(content).strip()
        if not text:
            logger.warning("Empty content provided for embedding - using fallback")
            return self._create_hash_fallback(text)
        
        try:
            if self.model is not None:
                # Use sentence-transformers model
                embedding = self.model.encode(text, convert_to_numpy=True)
                
                # Resize to target dimensions if needed
                embedding = self._resize_embedding(embedding)
                
                logger.debug(f"Generated local embedding (dim: {len(embedding)}) for text length {len(text)}")
                return embedding
            
            else:
                # Fallback to hash-based embedding
                logger.debug("Using hash-based fallback embedding (model unavailable)")
                return self._create_hash_fallback(text)
                
        except Exception as e:
            logger.error(f"Local embedding generation failed: {e}")
            return self._create_hash_fallback(text)
    
    def generate_embeddings(self, contents: List[Union[str, bytes]], content_types: Optional[List[str]] = None) -> List[np.ndarray]:
        """
        Generate embeddings for multiple contents.
        
        Args:
            contents: List of content to embed
            content_types: List of content types (optional)
            
        Returns:
            List of embedding vectors
        """
        if content_types is None:
            content_types = ["text"] * len(contents)
        
        embeddings = []
        for i, (content, content_type) in enumerate(zip(contents, content_types)):
            try:
                embedding = self.generate_embedding(content, content_type)
                embeddings.append(embedding)
                logger.debug(f"Generated embedding {i+1}/{len(contents)} for {content_type}")
            except Exception as e:
                logger.error(f"Failed to generate embedding {i+1}: {e}")
                # Use zero embedding as fallback
                embeddings.append(np.zeros(self.min_dimensions, dtype=np.float32))
        
        logger.info(f"Generated {len(embeddings)} local embeddings")
        return embeddings
    
    def _resize_embedding(self, embedding: np.ndarray) -> np.ndarray:
        """Resize embedding to target dimensions."""
        current_dim = len(embedding)
        
        if current_dim == self.min_dimensions:
            return embedding
        
        elif current_dim > self.min_dimensions:
            # Truncate
            resized = embedding[:self.min_dimensions]
            logger.debug(f"Truncated embedding from {current_dim} to {self.min_dimensions} dimensions")
            return resized
        
        else:
            # Pad with zeros
            padding = np.zeros(self.min_dimensions - current_dim, dtype=np.float32)
            resized = np.concatenate([embedding, padding])
            logger.debug(f"Padded embedding from {current_dim} to {self.min_dimensions} dimensions")
            return resized
    
    def _create_hash_fallback(self, text: str) -> np.ndarray:
        """Create fallback embedding using text hashing when model fails."""
        logger.warning("Using hash-based fallback embedding")
        
        try:
            import hashlib
            
            # Create multiple hashes for more dimensions
            hashes = []
            for i in range(0, len(text), len(text)//4 or 1):  # Create 4 hash segments
                segment = text[i:i + (len(text)//4 or 1)]
                if segment:
                    hash_val = hashlib.md5(segment.encode('utf-8')).digest()
                    hashes.extend(list(hash_val))
            
            # Convert to float32
            if hashes:
                embedding = np.array(hashes[:128], dtype=np.float32)  # Limit to 128 bytes max
            else:
                embedding = np.array(list(hashlib.md5(b"fallback").digest()), dtype=np.float32)
            
            # Resize to target dimensions
            embedding = self._resize_embedding(embedding)
            
            # Scale to reasonable range and ensure non-zero
            embedding = np.clip(embedding / 255.0, -0.5, 0.5)
            
            # Add small random variation to avoid identical embeddings
            np.random.seed(hash(text) % (2**32))
            noise = np.random.normal(0, 0.01, len(embedding))
            embedding += noise
            
            logger.debug(f"Created hash fallback embedding (dim: {len(embedding)})")
            return embedding
            
        except Exception as fallback_e:
            logger.error(f"Hash fallback failed: {fallback_e}")
            # Ultimate fallback: simple pattern
            pattern = np.linspace(0.1, 0.3, self.min_dimensions)
            return pattern.astype(np.float32)

    def filter_embeddings(self, embeddings: List[np.ndarray], contents: List[str]) -> List[np.ndarray]:
        """
        Filter out low-quality embeddings (all zeros or very low variance).
        
        Args:
            embeddings: List of embedding vectors
            contents: Corresponding content for logging
            
        Returns:
            List of valid embeddings
        """
        valid_embeddings = []
        for i, embedding in enumerate(embeddings):
            # Check if embedding is all zeros
            if np.allclose(embedding, 0):
                logger.warning(f"Filtering out zero embedding for content {i}: {contents[i][:50]}...")
                continue
            
            # Check embedding variance (too uniform might be bad)
            variance = np.var(embedding)
            if variance < 1e-6:
                logger.warning(f"Filtering out low-variance embedding (var: {variance:.2e}) for content {i}")
                continue
            
            valid_embeddings.append(embedding)
        
        if len(valid_embeddings) < len(embeddings):
            logger.info(f"Filtered {len(embeddings) - len(valid_embeddings)} low-quality embeddings")
        
        return valid_embeddings