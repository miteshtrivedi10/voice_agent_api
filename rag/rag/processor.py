from typing import List, Dict, Any, Optional, Tuple, Awaitable
import logging
import os
import asyncio
import numpy as np
from pathlib import Path
from functools import lru_cache
import hashlib
from dataclasses import dataclass
from typing import Set, Dict as TypeDict

from rag.rag.document_parser import DocumentParser
from rag.config.settings import settings
from rag.utils.file_handler import FileHandler
from rag.utils.exceptions import FileProcessingError
from rag.processors.image_processor import ImageModalProcessor
from rag.processors.table_processor import TableModalProcessor
from rag.processors.equation_processor import EquationModalProcessor
from rag.processors.generic_processor import GenericModalProcessor
from rag.rag.openrouter import OpenRouterClient
from rag.rag.nomic_embedding import NomicEmbeddingGenerator
from rag.rag.storage import MilvusStorage
from rag.rag.performance_monitor import PerformanceTimer, get_global_monitor
from rag.rag.questionnaire_generator import QuestionnaireGenerator

logger = logging.getLogger(__name__)

@dataclass
class SemanticRelation:
    """Data class for semantic relationships between content elements."""
    source_id: str
    target_id: str
    relation_type: str  # "describes", "illustrates", "supports", "contains", etc.
    strength: float  # 0.0-1.0 confidence
    direction: str  # "text_to_visual", "visual_to_text", "bidirectional"
    rationale: str  # Brief explanation
    page_id: str  # Shared page identifier
    spatial_proximity: float  # Normalized distance metric

class RAGProcessor:
    """Production-ready RAG processor with async multimodal analysis and semantic grouping."""

    # Define supported relationship types between content elements
    RELATION_TYPES = {
        "describes": "Text element describes visual content",
        "illustrates": "Visual element illustrates textual concept", 
        "supports": "Element provides supporting evidence or example",
        "contains": "Container element includes subordinate elements",
        "references": "Element references or cites another",
        "explains": "Element provides explanation for another",
        "demonstrates": "Element shows practical application of concept"
    }

    def __init__(self, storage: Optional[MilvusStorage] = None, 
                 vision_model_func=None, llm_model_func=None,
                 cache_size: int = 512, enable_async: bool = True, 
                 max_group_size: int = 5, relation_threshold: float = 0.6):
        """
        Initialize the enhanced RAG processor with OpenRouter Sonoma and Nomic Ollama integration.

        Args:
            storage: Milvus storage instance
            vision_model_func: Function for vision model analysis (optional)
            llm_model_func: Function for LLM content analysis (optional)
            cache_size: LRU cache size for processed content and relationships
            enable_async: Enable async processing for performance
            max_group_size: Maximum elements per semantic group
            relation_threshold: Minimum confidence for detected relationships
        """
        # Core components
        self.parser = DocumentParser()
        self.working_dir = settings.WORKING_DIR
        self.enable_async = enable_async
        self.max_group_size = max_group_size
        self.relation_threshold = relation_threshold

        # Model functions for processors
        self.vision_model_func = vision_model_func
        self.llm_model_func = llm_model_func

        # Initialize components
        self.storage = storage or MilvusStorage(
            uri=settings.MILVUS_URI, 
            token=settings.MILVUS_TOKEN
        )
        self.file_handler = FileHandler()
        self.performance_monitor = get_global_monitor()
        
        # Initialize content processors for different modalities
        self.processors = {
            "image": ImageModalProcessor(vision_model_func=self.vision_model_func),
            "table": TableModalProcessor(model_func=self.llm_model_func),
            "equation": EquationModalProcessor(model_func=self.llm_model_func),
            "generic": GenericModalProcessor(model_func=self.llm_model_func),
        }
        
        # Cache for processed content and relationships to improve performance
        self.content_cache = lru_cache(maxsize=cache_size)(self._get_cached_content)
        self.relation_cache = lru_cache(maxsize=cache_size)(self._get_cached_relations)
        
        # Performance tracking
        self.enable_profiling = getattr(settings, 'ENABLE_PROFILING', False)
        self.processor_stats = {}
        
        # Initialize questionnaire generator for educational content
        self.openrouter_client = OpenRouterClient()  # For questionnaire generation
        self.questionnaire_generator = QuestionnaireGenerator(
            openrouter_client=self.openrouter_client
        )
        
        logger.info("RAGProcessor initialized with multimodal analysis enabled")

    def process_directory(self, directory_path: str) -> Dict[str, List[Dict[str, Any]]]:
        """Process all files in a directory and return processed content by file."""
        directory = Path(directory_path)
        if not directory.exists() or not directory.is_dir():
            raise FileProcessingError(f"Directory not found: {directory_path}")
        
        results = {}
        files = list(directory.iterdir())
        
        for file_path in files:
            if file_path.suffix.lower() in ['.pdf', '.png', '.jpg', '.jpeg', '.bmp', '.tiff']:
                try:
                    content_items = self.process_file(str(file_path))
                    results[str(file_path)] = content_items
                    logger.info(f"Processed {file_path.name}: {len(content_items)} content items")
                except FileProcessingError as e:
                    logger.error(f"Failed to process {file_path}: {e}")
                    results[str(file_path)] = []
        
        return results

    def process_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Process a single file and return content items with embeddings."""
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileProcessingError(f"File not found: {file_path}")
        
        file_size = Path(file_path).stat().st_size
        with self.performance_monitor.track("file_processing", file_size):
            # Parse document
            raw_content = self.parser.parse_document(str(file_path))
            
            if not raw_content:
                logger.warning(f"No content extracted from {file_path}")
                return []
            
            # Process content items
            processed_content = []
            for item in raw_content:
                try:
                    processed_item = self._process_content_item(item)
                    if processed_item:
                        processed_content.append(processed_item)
                except Exception as e:
                    logger.error(f"Failed to process content item from {file_path}: {e}")
            
            # Store embeddings
            if processed_content:
                self._store_content_batch(processed_content)
                
                # Generate and print questionnaires for each processed content item
                self.questionnaire_generator.generate_and_print_questionnaires(processed_content)
            
            logger.info(f"Processed {len(processed_content)} content items from {file_path}")
            return processed_content

    def _process_content_item(self, content_item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a single content item through the appropriate pipeline."""
        content_type = content_item.get("type", "generic")
        
        # Get appropriate processor
        processor = self.processors.get(content_type, self.processors["generic"])
        
        try:
            # Debug: Print the original content item flags
            logger.debug(f"Processing content item: type={content_type}, is_page_image={content_item.get('is_page_image')}, is_component={content_item.get('is_component')}")
            
            # Generate description/enhanced content
            # Use multimodal processing for images to actually call the vision model
            if content_type == "image":
                # Always use multimodal processing for images to get proper analysis
                enhanced_item = processor.process_multimodal_content(content_item)
            else:
                enhanced_item = processor.generate_description_only(content_item)
            
            if not enhanced_item:
                return None
            
            # Generate embedding
            embedding = self._generate_embedding(enhanced_item)
            if embedding is None:
                return None
            
            # Add embedding to item
            if embedding is not None:
                enhanced_item["embedding"] = embedding.tolist()
            enhanced_item["source_file"] = content_item.get("source_file", "")
            enhanced_item["page_id"] = content_item.get("page", 1)
            
            # Ensure we have text content for storage
            if "text_content" not in enhanced_item:
                enhanced_item["text_content"] = enhanced_item.get("enhanced_text", "") or enhanced_item.get("text", "") or f"Image from {enhanced_item.get('source_file', 'unknown')}, page {enhanced_item.get('page_id', 'unknown')}"
            
            # Preserve our custom flags in metadata if they exist
            if "metadata" not in enhanced_item:
                enhanced_item["metadata"] = {}
            
            if content_item.get("is_page_image"):
                enhanced_item["metadata"]["is_page_image"] = True
            if content_item.get("is_component"):
                enhanced_item["metadata"]["is_component"] = True
            if content_item.get("from_ocr"):
                enhanced_item["metadata"]["from_ocr"] = True
                
            # Debug: Print the enhanced item flags
            logger.debug(f"Enhanced item metadata flags: is_page_image={enhanced_item['metadata'].get('is_page_image')}, is_component={enhanced_item['metadata'].get('is_component')}")
                
            return enhanced_item
            
        except Exception as e:
            logger.error(f"Processing failed for {content_type} item: {e}")
            return None

    def _generate_embedding(self, content_item: Dict[str, Any]) -> Optional[np.ndarray]:
        """
        Generate embedding for content item using NomicEmbeddingGenerator.
        """
        try:
            # Use the embedding generator from the class instance
            if not hasattr(self, '_embedding_generator'):
                self._embedding_generator = NomicEmbeddingGenerator()
            
            content_text = content_item.get("text", "") or content_item.get("enhanced_text", "")
            if not content_text:
                logger.warning("No text content for embedding generation")
                return None
            
            # Generate embedding
            embeddings = self._embedding_generator.generate_embeddings([content_text])
            if embeddings and len(embeddings) > 0:
                return embeddings[0]
            else:
                logger.warning("Failed to generate embedding")
                return None
                
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return None

    async def _process_content_item_async(self, content_item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Async version of content item processing."""
        # For now, use synchronous processing
        return self._process_content_item(content_item)

    def _store_content_batch(self, content_items: List[Dict[str, Any]]):
        """Store processed content items with embeddings in batch."""
        try:
            # Prepare data for batch insert
            embeddings_data = []
            for item in content_items:
                if "embedding" in item:
                    # Ensure we have proper text content for storage
                    text_content = (item.get("text_content") or 
                                  item.get("enhanced_text") or 
                                  item.get("text") or
                                  f"Content from {item.get('source_file', 'unknown')}, page {item.get('page_id', 'unknown')}")
                    
                    embeddings_data.append({
                        "embedding": item["embedding"],
                        "text_content": text_content[:65535],
                        "content_type": item.get("type", "generic"),
                        "source_file": item.get("source_file", ""),
                        "page_id": str(item.get("page_id", 1)),
                        "metadata": item.get("metadata", {}),
                        "processing_timestamp": item.get("processing_timestamp")
                    })
            
            if embeddings_data:
                doc_ids = self.storage.insert_batch(embeddings_data)
                logger.debug(f"Stored {len(doc_ids)} content items")
        except Exception as e:
            logger.error(f"Failed to store content batch: {e}")

    def search_similar_content(self, query: str, top_k: int = 5, 
                              content_types: Optional[List[str]] = None, 
                              source_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for content similar to the query.
        """
        try:
            # Use the embedding generator from the class instance
            if not hasattr(self, '_embedding_generator'):
                self._embedding_generator = NomicEmbeddingGenerator()
            
            query_embedding = self._embedding_generator.generate_embeddings([query])
            if not query_embedding or len(query_embedding) == 0:
                logger.warning("Failed to generate query embedding")
                return []
            
            # Search in storage
            results = self.storage.search_similar_content(
                query_embedding[0].tolist(),
                top_k=top_k,
                content_types=content_types,
                source_filter=source_filter
            )
            
            logger.info(f"Search returned {len(results)} results for query: {query[:50]}...")
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise FileProcessingError(f"Search failed: {e}")

    def _get_cached_content(self, content_hash: str) -> Optional[Dict[str, Any]]:
        """Get cached content by hash."""
        # Implementation depends on cache storage
        return None

    def _get_cached_relations(self, relation_key: str) -> Optional[List[SemanticRelation]]:
        """Get cached relations by key."""
        # Implementation depends on cache storage
        return None

    def detect_semantic_relations(self, content_items: List[Dict[str, Any]]) -> List[SemanticRelation]:
        """Detect semantic relationships between content items."""
        relations = []
        
        # Simple spatial proximity based relations for now
        for i, item1 in enumerate(content_items):
            for j, item2 in enumerate(content_items[i+1:], i+1):
                if item1.get("page") == item2.get("page"):
                    # Calculate spatial proximity (simplified)
                    proximity = self._calculate_spatial_proximity(item1, item2)
                    
                    if proximity > 0.7:  # Threshold for close proximity
                        relation = SemanticRelation(
                            source_id=item1["id"],
                            target_id=item2["id"],
                            relation_type="contains" if item1.get("type") == "text" else "illustrates",
                            strength=proximity,
                            direction="bidirectional",
                            rationale=f"Spatial proximity on page {item1.get('page')}",
                            page_id=str(item1.get("page")),
                            spatial_proximity=proximity
                        )
                        relations.append(relation)
        
        logger.debug(f"Detected {len(relations)} semantic relations")
        return relations

    def _calculate_spatial_proximity(self, item1: Dict, item2: Dict) -> float:
        """Calculate spatial proximity between two content items (simplified)."""
        coords1 = item1.get("coordinates", {})
        coords2 = item2.get("coordinates", {})
        
        if not coords1 or not coords2:
            return 0.0
        
        # Simple overlap calculation
        x1, y1, w1, h1 = coords1.get("x", 0), coords1.get("y", 0), coords1.get("width", 0), coords1.get("height", 0)
        x2, y2, w2, h2 = coords2.get("x", 0), coords2.get("y", 0), coords2.get("width", 0), coords2.get("height", 0)
        
        # Calculate intersection area
        inter_x = max(0, min(x1 + w1, x2 + w2) - max(x1, x2))
        inter_y = max(0, min(y1 + h1, y2 + h2) - max(y1, y2))
        intersection = inter_x * inter_y
        
        # Calculate union area
        area1 = w1 * h1
        area2 = w2 * h2
        union = area1 + area2 - intersection
        
        if union == 0:
            return 0.0
        
        return intersection / union

    async def process_directory_async(self, directory_path: str) -> Dict[str, List[Dict[str, Any]]]:
        """Async version of directory processing."""
        if not self.enable_async:
            return self.process_directory(directory_path)
        
        # Async implementation would go here
        return self.process_directory(directory_path)

    def __del__(self):
        """Cleanup resources when object is deleted."""
        try:
            if hasattr(self, '_embedding_generator'):
                # Close the embedding generator's aiohttp session
                try:
                    loop = asyncio.get_event_loop()
                    if not loop.is_closed():
                        loop.run_until_complete(self._embedding_generator.close())
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"Error in processor destructor: {e}")

    def get_processor_stats(self) -> Dict[str, Any]:
        """Get statistics about processor usage."""
        return {
            "total_content_processed": sum(self.processor_stats.values()),
            "processors_used": list(self.processor_stats.keys()),
            "enable_async": self.enable_async,
            "cache_size": self.content_cache.cache_info()
        }