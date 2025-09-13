import os
import hashlib
import logging
import asyncio
import aiohttp
import json
import numpy as np
import httpx
from typing import List, Dict, Any, Optional, Union
from .embedding import BaseEmbeddingGenerator
from rag.config.settings import settings
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

logger = logging.getLogger(__name__)


class NomicEmbeddingGenerator(BaseEmbeddingGenerator):
    """Production-ready embedding generator using Ollama's nomic-embed-text model with fallback support."""

    MODEL_NAME = "nomic-embed-text"
    EXPECTED_DIMENSIONS = 768
    BATCH_SIZE = 8  # Optimal batch size for Ollama performance
    MAX_BATCH_CONCURRENCY = 2  # Limit concurrent batches to avoid overwhelming Ollama

    # def __init__(
    #     self,
    #     ollama_url: Optional[str] = None,
    #     min_dimensions: int = EXPECTED_DIMENSIONS,
    #     fallback_model: str = "all-MiniLM-L6-v2",
    #     enable_fallback: bool = True,
    #     request_delay: float = 0.1,
    # ):
    #     """
    #     Initialize the Nomic embedding generator with Ollama integration and fallback.

    #     Args:
    #         ollama_url: Ollama server URL (defaults to settings.OLLAMA_BASE_URL)
    #         min_dimensions: Minimum embedding dimensions (defaults to 768 for nomic-embed-text)
    #         fallback_model: Sentence-transformers fallback model name
    #         enable_fallback: Enable fallback to sentence-transformers if Ollama unavailable
    #         request_delay: Delay between requests for rate limiting
    #     """
    #     super().__init__("nomic-embed-text", min_dimensions)
    #     self.ollama_url = ollama_url or settings.OLLAMA_BASE_URL
    #     self.enable_fallback = enable_fallback
    #     self.fallback_model = fallback_model
    #     self.request_delay = request_delay
    #     self.session = None
    #     self.semaphore = asyncio.Semaphore(self.MAX_BATCH_CONCURRENCY)
    #     self.model_available = None
    #     self.last_request_time = 0.0
    #     self._validate_ollama_connection()

    DEFAULT_REQUEST_DELAY = 0.1

    def __init__(
        self,
        ollama_url: Optional[str] = None,
        min_dimensions: int = EXPECTED_DIMENSIONS,
        fallback_model: str = "all-MiniLM-L6-v2",
        enable_fallback: bool = True,
        request_delay: float = 0.1,
    ):
        """
        Initialize the Nomic embedding generator with Ollama integration and fallback.

        Args:
            ollama_url: Ollama server URL (defaults to settings.OLLAMA_BASE_URL)
            min_dimensions: Minimum embedding dimensions (defaults to 768 for nomic-embed-text)
            fallback_model: Sentence-transformers fallback model name
            enable_fallback: Enable fallback to sentence-transformers if Ollama unavailable
        """
        super().__init__("nomic-embed-text", min_dimensions)
        self.ollama_url = ollama_url or settings.OLLAMA_BASE_URL
        self.enable_fallback = enable_fallback
        self.fallback_model = fallback_model
        self.session = None
        self.semaphore = asyncio.Semaphore(self.MAX_BATCH_CONCURRENCY)
        self.model_available = None
        self.request_delay = request_delay
        self.last_request_time = 0.0
        self._validate_ollama_connection()

        # No fallback - raise error if Ollama fails
        self.fallback_model_instance = None
        self.enable_fallback = False

        logger.info(
            f"NomicEmbeddingGenerator initialized - Ollama: {self.ollama_url}, Fallback: {self.enable_fallback}"
        )

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session with connection pooling."""
        if self.session is None or self.session.closed:
            connector = aiohttp.TCPConnector(
                limit=20, limit_per_host=10, ttl_dns_cache=300
            )
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={"Content-Type": "application/json"},
            )
            logger.debug("New aiohttp session created for Ollama")
        return self.session

    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.debug("Aiohttp session closed")
            
    def __del__(self):
        """Cleanup aiohttp session when object is deleted."""
        try:
            # Use existing event loop if available, otherwise create a new one
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    return
            except RuntimeError:
                loop = asyncio.new_event_loop()
            
            if self.session and not self.session.closed:
                if loop.is_running():
                    # If loop is running, schedule the close coroutine
                    loop.create_task(self.session.close())
                else:
                    # If loop is not running, run the close coroutine
                    loop.run_until_complete(self.session.close())
                logger.debug("Aiohttp session closed in destructor")
        except Exception as e:
            logger.debug(f"Error closing aiohttp session in destructor: {e}")

    def _validate_ollama_connection(self):
        """Validate Ollama server availability and model presence."""
        try:
            response = httpx.get(f"{self.ollama_url}/api/tags", timeout=10)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                if any(self.MODEL_NAME in name for name in model_names):
                    self.model_available = True
                    logger.info(f"Ollama model '{self.MODEL_NAME}' available")
                else:
                    self.model_available = False
                    logger.warning(
                        f"Ollama model '{self.MODEL_NAME}' not found. Available: {model_names}"
                    )
            else:
                self.model_available = False
                logger.error(f"Ollama server unavailable: {response.status_code}")
        except Exception as e:
            self.model_available = False
            logger.error(f"Failed to validate Ollama connection: {e}")
            if self.enable_fallback:
                logger.info("Fallback to sentence-transformers enabled")

    def generate_embedding(
        self, content: Union[str, bytes], content_type: str = "text"
    ) -> np.ndarray:
        """
        Generate embedding synchronously (for compatibility). Use async_generate_embedding for production.

        Args:
            content: Text content to embed (image bytes not supported)
            content_type: Must be "text"

        Returns:
            Embedding vector as numpy array
        """
        if content_type != "text" or isinstance(content, bytes):
            logger.warning(
                "Nomic embedding only supports text content. Returning fallback."
            )
            return self._create_fallback_embedding(
                content if isinstance(content, str) else str(content)
            )

        # Use existing event loop if available, otherwise create a new one
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.async_generate_embedding(content))

    async def async_generate_embedding(
        self, content: Union[str, bytes], content_type: str = "text"
    ) -> np.ndarray:
        """
        Generate embedding asynchronously with Ollama nomic-embed-text.

        Args:
            content: Text content to embed
            content_type: Must be "text"

        Returns:
            Embedding vector as numpy array
        """
        if content_type != "text":
            logger.warning(f"Nomic embedding only supports text, got: {content_type}")
            return self._create_fallback_embedding(content)

        if not content.strip():
            logger.warning("Empty content provided for embedding")
            return np.zeros(self.min_dimensions, dtype=np.float32)

        # Single item embedding
        embedding = await self._generate_single_embedding(content)

        # Validate and normalize
        embedding = self._validate_and_normalize_embedding(embedding, content)

        return embedding

    def generate_embeddings(
        self,
        contents: List[Union[str, bytes]],
        content_types: Optional[List[str]] = None,
    ) -> List[np.ndarray]:
        """
        Generate embeddings for multiple texts with batching and concurrency control.

        Args:
            contents: List of text strings to embed
            content_types: List of "text" (ignored for compatibility)

        Returns:
            List of embedding vectors
        """
        if content_types is None:
            content_types = ["text"] * len(contents)

        # Filter and validate input
        valid_contents = []
        for i, (content, ctype) in enumerate(zip(contents, content_types)):
            if ctype != "text":
                logger.warning(f"Skipping non-text content at index {i}: {ctype}")
                valid_contents.append("")
            elif isinstance(content, str) and content.strip():
                valid_contents.append(content.strip())
            else:
                logger.warning(f"Skipping empty/invalid content at index {i}")
                valid_contents.append("")

        if not valid_contents:
            logger.warning("No valid content for embedding generation")
            return [np.zeros(self.min_dimensions, dtype=np.float32)] * len(contents)

        # Batch processing with concurrency control
        try:
            # Use existing event loop if available, otherwise create a new one
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    raise RuntimeError("Event loop is closed")
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            embeddings = loop.run_until_complete(self._batch_generate_embeddings(valid_contents))
        except Exception as e:
            logger.error(f"Batch embedding generation failed: {e}")
            # Fallback to individual embedding generation
            embeddings = []
            for content in valid_contents:
                try:
                    # Use existing event loop if available, otherwise create a new one
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_closed():
                            raise RuntimeError("Event loop is closed")
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    
                    embedding = loop.run_until_complete(self.async_generate_embedding(content))
                    embeddings.append(embedding)
                except Exception as inner_e:
                    logger.error(f"Individual embedding generation failed: {inner_e}")
                    embeddings.append(np.zeros(self.min_dimensions, dtype=np.float32))

        # Pad to original length
        while len(embeddings) < len(contents):
            embeddings.append(np.zeros(self.min_dimensions, dtype=np.float32))

        # Filter low-quality embeddings
        valid_embeddings = self.filter_embeddings(embeddings[: len(contents)], contents)

        logger.info(
            f"Generated {len(embeddings)} embeddings, {len(valid_embeddings)} valid after filtering"
        )
        return valid_embeddings

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type(
            (aiohttp.ClientError, asyncio.TimeoutError, json.JSONDecodeError)
        ),
        reraise=True,
    )
    async def _generate_single_embedding(self, text: Union[str, bytes]) -> np.ndarray:
        """Generate single embedding with retry logic."""
        async with self.semaphore:
            session = await self._get_session()

            # Apply rate limiting
            await self._apply_async_rate_limiting()

            payload = {
                "model": self.MODEL_NAME,
                "prompt": text,
                "options": {
                    "temperature": 0.0,  # Deterministic embeddings
                    "top_p": 1.0,
                },
            }

            url = f"{self.ollama_url}/api/embeddings"
            logger.debug(f"Generating embedding for text (length: {len(text)})")

            try:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        embedding = np.array(data["embedding"], dtype=np.float32)

                        # Normalize to unit length (common for embeddings)
                        norm = np.linalg.norm(embedding)
                        if norm > 0:
                            embedding = (embedding / norm).astype(np.float32)

                        logger.debug(
                            f"Generated embedding with {len(embedding)} dimensions"
                        )
                        return embedding
                    else:
                        error_text = await response.text()
                        logger.error(
                            f"Ollama embedding error {response.status}: {error_text}"
                        )

                        if response.status == 404:
                            raise ValueError(
                                f"Model '{self.MODEL_NAME}' not found in Ollama"
                            )
                        elif response.status == 503:
                            raise aiohttp.ClientError("Ollama service unavailable")
                        else:
                            raise aiohttp.ClientError(
                                f"HTTP {response.status}: {error_text}"
                            )

            except asyncio.TimeoutError:
                logger.error("Ollama embedding request timed out")
                raise
            except aiohttp.ClientError as e:
                logger.error(f"Ollama client error: {e}")
                raise
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error from Ollama: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error in embedding generation: {e}")
                raise

    async def _batch_generate_embeddings(self, texts: List[str]) -> List[np.ndarray]:
        """Generate embeddings for batch of texts with optimal concurrency."""
        if not texts:
            return []

        # Split into batches
        batches = [
            texts[i : i + self.BATCH_SIZE]
            for i in range(0, len(texts), self.BATCH_SIZE)
        ]
        all_embeddings = []

        for batch_idx, batch_texts in enumerate(batches):
            logger.debug(
                f"Processing batch {batch_idx + 1}/{len(batches)} with {len(batch_texts)} texts"
            )

            # Process batch concurrently but limit total concurrency
            tasks = [self._generate_single_embedding(text) for text in batch_texts]
            batch_embeddings = await asyncio.gather(*tasks, return_exceptions=True)

            # Handle exceptions in batch
            for i, result in enumerate(batch_embeddings):
                if isinstance(result, Exception):
                    logger.warning(
                        f"Batch embedding {batch_idx * self.BATCH_SIZE + i} failed: {result}"
                    )
                    batch_embeddings[i] = np.zeros(
                        self.min_dimensions, dtype=np.float32
                    )
                elif not isinstance(result, np.ndarray) or len(result) == 0:
                    logger.warning(f"Invalid embedding result at batch position {i}")
                    batch_embeddings[i] = np.zeros(
                        self.min_dimensions, dtype=np.float32
                    )

            all_embeddings.extend(batch_embeddings)
            valid_count = sum(
                1 for e in batch_embeddings if isinstance(e, np.ndarray) and len(e) > 0
            )
            logger.debug(
                f"Batch {batch_idx + 1} completed with {valid_count} valid embeddings"
            )

        return all_embeddings

    async def _apply_async_rate_limiting(self):
        """Apply asynchronous rate limiting."""
        current_time = asyncio.get_event_loop().time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.request_delay:
            wait_time = self.request_delay - time_since_last
            logger.debug(f"Async rate limiting: waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)

        self.last_request_time = asyncio.get_event_loop().time()

    def _validate_and_normalize_embedding(
        self, embedding: np.ndarray, original_text: Union[str, bytes]
    ) -> np.ndarray:
        """Validate embedding quality and normalize dimensions."""
        if embedding is None or not isinstance(embedding, np.ndarray):
            logger.warning("Invalid embedding returned, using fallback")
            return self._create_fallback_embedding(original_text)

        # Check dimensions
        if len(embedding) < self.min_dimensions:
            logger.warning(
                f"Embedding too short ({len(embedding)} < {self.min_dimensions}), padding"
            )
            padding = np.zeros(self.min_dimensions - len(embedding), dtype=np.float32)
            embedding = np.concatenate([embedding, padding])
        elif len(embedding) > self.min_dimensions:
            logger.debug(
                f"Truncating embedding from {len(embedding)} to {self.min_dimensions}"
            )
            embedding = embedding[: self.min_dimensions]

        # Check for invalid values
        if not np.isfinite(embedding).all():
            logger.warning("Embedding contains NaN/inf values, replacing with fallback")
            return self._create_fallback_embedding(original_text)

        # Check if all zeros (invalid embedding)
        if np.allclose(embedding, 0):
            logger.warning("Generated all-zero embedding, using fallback")
            return self._create_fallback_embedding(original_text)

        # Normalize to unit length if not already
        norm = np.linalg.norm(embedding)
        if norm > 0 and not np.isclose(norm, 1.0):
            embedding = embedding / norm

        # Final validation
        if self.validate_embedding(embedding):
            logger.debug(
                f"Validated embedding: {len(embedding)} dimensions, norm: {np.linalg.norm(embedding):.3f}"
            )
            return embedding
        else:
            logger.warning("Embedding failed final validation, using fallback")
            return self._create_fallback_embedding(original_text)

    def _create_fallback_embedding(self, text: Union[str, bytes]) -> np.ndarray:
        """Create high-quality fallback embedding using sentence-transformers or hash-based method."""
        text_str = text.decode("utf-8") if isinstance(text, bytes) else str(text)
        if self.enable_fallback and self.fallback_model_instance is not None:
            try:
                # Use sentence-transformers fallback
                embedding = self.fallback_model_instance.encode(
                    text_str, convert_to_numpy=True
                )

                # Normalize dimensions to match nomic
                if len(embedding) != self.min_dimensions:
                    if len(embedding) < self.min_dimensions:
                        padding = np.zeros(
                            self.min_dimensions - len(embedding), dtype=np.float32
                        )
                        embedding = np.concatenate([embedding, padding])
                    else:
                        embedding = embedding[: self.min_dimensions]

                # Validate and normalize the fallback embedding
                embedding = self._validate_and_normalize_embedding(embedding, text)

                logger.info(
                    f"Fallback embedding generated with {len(embedding)} dimensions"
                )
                return embedding
            except Exception as e:
                logger.error(f"Sentence-transformers fallback failed: {e}")
                self.enable_fallback = False

        # Final fallback: simple hash-based embedding
        logger.warning("Using hash-based fallback embedding (low quality)")
        return self._create_hash_embedding(text)

    def _create_hash_embedding(self, text: Union[str, bytes]) -> np.ndarray:
        text_str = text.decode("utf-8") if isinstance(text, bytes) else str(text)
        """Create robust hash-based embedding as last resort fallback using multiple hash functions."""
        if not text_str.strip():
            # Return zero embedding for empty text
            return np.zeros(self.min_dimensions, dtype=np.float32)

        # Use multiple hash functions to create better distribution
        hashes = []
        for hash_func in [hashlib.md5, hashlib.sha1, hashlib.sha256]:
            hash_obj = hash_func(text_str.encode("utf-8"))
            hash_hex = hash_obj.hexdigest()
            # Convert to normalized floats (0.0 to 1.0)
            hash_values = [
                float(int(hash_hex[i : i + 2], 16)) / 255.0
                for i in range(0, len(hash_hex), 2)
            ]
            hashes.extend(hash_values)

        # Take first min_dimensions values, cycling if needed
        embedding_values = hashes[: self.min_dimensions]
        if len(embedding_values) < self.min_dimensions:
            # Cycle through available values to fill dimensions
            cycle_needed = self.min_dimensions - len(embedding_values)
            embedding_values.extend(hashes[:cycle_needed])

        embedding = np.array(embedding_values, dtype=np.float32)

        # Add character-level features for better text representation
        if len(text_str) > 0:
            # Simple character distribution features
            char_counts = (
                np.bincount([ord(c) % 256 for c in text_str[:100]], minlength=256)
                / 256.0
            )  # Normalize
            # Add to embedding (mix with existing values)
            char_features = char_counts[: min(128, self.min_dimensions)]
            if len(char_features) > 0:
                mix_ratio = 0.3  # Blend character features
                for i in range(min(len(embedding), len(char_features))):
                    embedding[i] = (1 - mix_ratio) * embedding[
                        i
                    ] + mix_ratio * char_features[i]

        # Ensure all values are finite
        embedding = np.nan_to_num(embedding, nan=0.0, posinf=1.0, neginf=-1.0)

        # Normalize to unit length
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        else:
            # Fallback normalization if all zeros
            embedding = np.full(
                self.min_dimensions,
                1.0 / np.sqrt(self.min_dimensions),
                dtype=np.float32,
            )

        logger.debug(
            f"Enhanced hash-based embedding created: {len(embedding)} dimensions, norm: {np.linalg.norm(embedding):.3f}"
        )
        return embedding
