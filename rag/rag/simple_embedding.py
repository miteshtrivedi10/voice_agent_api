"""Simple synchronous embedding generator for testing."""
import numpy as np
import requests
from typing import List, Union
from logic.logging_config import configured_logger as logger

class SimpleEmbeddingGenerator:
    """Simple synchronous embedding generator using Ollama's nomic-embed-text model."""
    
    def __init__(self, ollama_url: str = "http://localhost:11434", model_name: str = "nomic-embed-text"):
        self.ollama_url = ollama_url
        self.model_name = model_name
        logger.info(f"SimpleEmbeddingGenerator initialized with Ollama URL: {ollama_url}, Model: {model_name}")
    
    def generate_embedding(self, text: str) -> np.ndarray:
        """Generate embedding synchronously using nomic-embed-text model."""
        if not text or not text.strip():
            logger.warning("Empty or whitespace-only text provided for embedding generation")
            return np.zeros(768, dtype=np.float32)
        
        # Clean and prepare text for better embedding quality
        cleaned_text = self._clean_text(text)
        
        if len(cleaned_text) < 10:
            logger.warning(f"Very short text ({len(cleaned_text)} chars) for embedding generation: '{cleaned_text}'")
        
        try:
            payload = {
                "model": self.model_name,
                "prompt": cleaned_text,
                "options": {
                    "temperature": 0.0,  # Deterministic embeddings
                    "top_p": 1.0,
                },
            }
            
            url = f"{self.ollama_url}/api/embeddings"
            logger.debug(f"Generating embedding for text (length: {len(cleaned_text)}) using {self.model_name}")
            
            response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                embedding = np.array(data["embedding"], dtype=np.float32)
                
                # Normalize to unit length for better semantic similarity
                norm = np.linalg.norm(embedding)
                if norm > 0:
                    embedding = (embedding / norm).astype(np.float32)
                
                logger.debug(f"Generated {self.model_name} embedding with {len(embedding)} dimensions")
                return embedding
            else:
                error_msg = f"Ollama API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                # Return zero vector as fallback
                return np.zeros(768, dtype=np.float32)
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error generating embedding: {e}")
            # Return zero vector as fallback
            return np.zeros(768, dtype=np.float32)
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            # Return zero vector as fallback
            return np.zeros(768, dtype=np.float32)
    
    def _clean_text(self, text: str) -> str:
        """Clean text for better embedding quality."""
        if not text:
            return ""
        
        # Remove excessive whitespace
        cleaned = " ".join(text.split())
        
        # Truncate very long text to prevent Ollama issues
        if len(cleaned) > 8192:  # Reasonable limit for embedding models
            logger.debug(f"Truncating text from {len(cleaned)} to 8192 characters for embedding")
            cleaned = cleaned[:8192]
        
        return cleaned
    
    def generate_embeddings(self, texts: List[str]) -> List[np.ndarray]:
        """Generate embeddings for multiple texts using nomic-embed-text model."""
        embeddings = []
        for i, text in enumerate(texts):
            logger.debug(f"Generating embedding {i+1}/{len(texts)}")
            embedding = self.generate_embedding(text)
            embeddings.append(embedding)
        return embeddings