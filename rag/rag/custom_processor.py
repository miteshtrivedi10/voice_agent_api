"""Custom RAG processor that uses simple synchronous embedding generation."""
import numpy as np
from typing import List, Dict, Any, Optional
from rag.rag.simple_embedding import SimpleEmbeddingGenerator
from rag.rag.processor import RAGProcessor
from logic.logging_config import configured_logger as logger

class CustomRAGProcessor(RAGProcessor):
    """Custom RAG processor with synchronous embedding generation and enhanced content analysis."""
    
    def __init__(self, storage=None, vision_model_func=None, llm_model_func=None, 
                 cache_size: int = 512, enable_async: bool = True, 
                 max_group_size: int = 5, relation_threshold: float = 0.6,
                 user_name: Optional[str] = None):
        """Initialize the custom RAG processor."""
        super().__init__(storage, vision_model_func, llm_model_func, cache_size, 
                         enable_async, max_group_size, relation_threshold, user_name)
        # Use our simple embedding generator for nomic-embed-text model
        self._embedding_generator = SimpleEmbeddingGenerator()
    
    def _process_content_item(self, content_item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a single content item through the appropriate pipeline with enhanced analysis."""
        content_type = content_item.get("type", "generic") or "generic"
        
        # Ensure content_type is a string
        if content_type is None:
            content_type = "generic"
        
        # Get appropriate processor
        processor = self.processors.get(content_type, self.processors["generic"])
        
        try:
            # Debug: Print the original content item flags
            logger.debug(f"Processing content item: type={content_type}, is_page_image={content_item.get('is_page_image')}, is_component={content_item.get('is_component')}")
            
            # Add size filtering for images
            if content_type == "image":
                image_data = content_item.get("data")
                if image_data:
                    # Convert to bytes if needed
                    if not isinstance(image_data, bytes):
                        import base64
                        try:
                            image_data = base64.b64decode(image_data)
                        except:
                            pass
                    
                    # Skip very small images
                    if isinstance(image_data, bytes) and len(image_data) < 1024:
                        logger.debug(f"Skipping small image ({len(image_data)} bytes) - likely icon/bullet")
                        # Treat as generic text content instead
                        content_type = "generic"
                        # Create enhanced text description for better embedding
                        enhanced_text = self._generate_enhanced_text_for_small_image(content_item)
                        enhanced_item = {
                            "text": enhanced_text,
                            "type": "generic",
                            "source_file": content_item.get("source_file", ""),
                            "page": content_item.get("page", 1),
                            "enhanced_text": enhanced_text,
                        }
                        return self.processors["generic"].generate_description_only(enhanced_item)
            
            # Generate description/enhanced content using LLMs
            # Use multimodal processing for images to actually call the vision model
            if content_type == "image":
                # Always use multimodal processing for images to get proper analysis from vision LLM
                enhanced_item = processor.process_multimodal_content(content_item)
            else:
                enhanced_item = processor.generate_description_only(content_item)
            
            if not enhanced_item:
                return None
            
            # Enhance the content further with cross-modal analysis
            enhanced_item = self._enhance_content_with_context(enhanced_item, content_item)
            
            # Generate high-quality embedding using nomic-embed-text
            embedding = self._generate_embedding(enhanced_item)
            if embedding is None:
                return None
            
            # Add embedding to item
            if embedding is not None:
                enhanced_item["embedding"] = embedding.tolist()
            enhanced_item["source_file"] = content_item.get("source_file", "")
            enhanced_item["page_id"] = content_item.get("page", 1)
            
            # Ensure we have rich text content for storage and questionnaire generation
            if "text_content" not in enhanced_item:
                enhanced_item["text_content"] = self._generate_rich_text_content(enhanced_item)
            
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
    
    def _generate_enhanced_text_for_small_image(self, content_item: Dict[str, Any]) -> str:
        """Generate enhanced text description for small images."""
        file_path = content_item.get("source_file", "unknown")
        page = content_item.get("page", "unknown")
        ocr_text = content_item.get("text", "")
        
        if ocr_text:
            return f"Small image/icon with OCR text: {ocr_text} (from {file_path}, page {page})"
        else:
            return f"Small decorative image/icon (from {file_path}, page {page})"
    
    def _enhance_content_with_context(self, enhanced_item: Dict[str, Any], original_item: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance content with additional context for better embeddings and questionnaires."""
        # Add structural context
        content_type = enhanced_item.get("type", "generic") or "generic"
        source_file = enhanced_item.get("source_file", "unknown") or "unknown"
        page_id = enhanced_item.get("page_id", "unknown") or "unknown"
        
        # Ensure content_type is a string before calling .upper()
        if content_type is None:
            content_type = "generic"
        else:
            content_type = str(content_type)
            
        # Ensure source_file and page_id are strings
        if source_file is None:
            source_file = "unknown"
        else:
            source_file = str(source_file)
            
        if page_id is None:
            page_id = "unknown"
        else:
            page_id = str(page_id)
        
        # Create rich metadata for better embedding quality
        if "metadata" not in enhanced_item:
            enhanced_item["metadata"] = {}
        
        enhanced_item["metadata"].update({
            "content_type": content_type,
            "source_document": source_file,
            "page_number": page_id,
            "processing_timestamp": self._get_timestamp(),
            "semantic_context": self._extract_semantic_context(enhanced_item),
        })
        
        # Enhance the text content with structural information
        base_text = enhanced_item.get("text", "") or enhanced_item.get("enhanced_text", "")
        if base_text:
            structural_prefix = f"[{content_type.upper()} from {source_file}, page {page_id}] "
            enhanced_item["enhanced_text"] = structural_prefix + base_text
            
        return enhanced_item
    
    def _extract_semantic_context(self, content_item: Dict[str, Any]) -> str:
        """Extract semantic context to improve embedding quality."""
        content_type = content_item.get("type", "generic") or "generic"
        
        # Ensure content_type is a string
        if content_type is None:
            content_type = "generic"
        else:
            content_type = str(content_type)
        
        metadata = content_item.get("metadata", {})
        
        context_parts = []
        
        # Add content type context
        context_parts.append(f"Content type: {content_type}")
        
        # Add visual analysis context for images
        if content_type == "image" and metadata.get("has_visual_analysis"):
            visual_analysis = metadata.get("visual_analysis", {})
            if isinstance(visual_analysis, dict):
                scene_type = visual_analysis.get("scene_type", "image")
                educational_concept = visual_analysis.get("educational_concept", "")
                if scene_type:
                    context_parts.append(f"Visual type: {scene_type}")
                if educational_concept:
                    context_parts.append(f"Educational focus: {educational_concept}")
        
        # Add complexity context
        complexity = metadata.get("complexity_level") or metadata.get("complexity", "medium")
        context_parts.append(f"Complexity: {complexity}")
        
        return " | ".join(context_parts)
    
    def _generate_rich_text_content(self, enhanced_item: Dict[str, Any]) -> str:
        """Generate rich text content that combines all available information for better embeddings."""
        # Combine all text sources
        text_parts = []
        
        # Main content
        main_text = enhanced_item.get("text", "")
        if main_text:
            text_parts.append(main_text)
        
        # Enhanced description
        enhanced_text = enhanced_item.get("enhanced_text", "")
        if enhanced_text and enhanced_text != main_text:
            text_parts.append(enhanced_text)
        
        # Metadata context
        metadata = enhanced_item.get("metadata", {})
        semantic_context = metadata.get("semantic_context", "")
        if semantic_context:
            text_parts.append(f"Context: {semantic_context}")
        
        # Visual analysis for images
        if enhanced_item.get("type") == "image" and metadata.get("has_visual_analysis"):
            visual_analysis = metadata.get("visual_analysis", {})
            if isinstance(visual_analysis, dict):
                description = visual_analysis.get("description", "")
                if description:
                    text_parts.append(f"Visual description: {description}")
        
        return " | ".join(text_parts) if text_parts else "Content not available"
    
    def _get_timestamp(self) -> str:
        """Get current timestamp for metadata."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def _generate_embedding(self, content_item: Dict[str, Any]) -> Optional[np.ndarray]:
        """
        Generate high-quality embedding using nomic-embed-text model.
        Combines rich text content for better semantic representation.
        """
        try:
            # Use the rich text content we generated for best embedding quality
            content_text = content_item.get("text_content", "") or \
                          content_item.get("enhanced_text", "") or \
                          content_item.get("text", "")
            
            if not content_text or len(content_text.strip()) < 10:
                logger.warning("Insufficient text content for embedding generation")
                # Create a minimal embedding for very short content
                content_text = content_text or "Minimal content"
            
            # Generate embedding using nomic-embed-text model via our simple generator
            embedding = self._embedding_generator.generate_embedding(content_text)
            if embedding is not None:
                logger.debug(f"Generated embedding with {len(embedding)} dimensions for content: {content_text[:50]}...")
                return embedding
            else:
                logger.warning("Failed to generate embedding, using fallback")
                # Return a zero vector as fallback
                return np.zeros(768, dtype=np.float32)
                
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            # Return a zero vector as fallback
            return np.zeros(768, dtype=np.float32)
    
    def process_file(self, file_path: str):
        """
        Enhanced process_file method that ensures high-quality content extraction
        for better questionnaire generation.
        """
        logger.info(f"Processing file with enhanced content extraction: {file_path}")
        
        # Call parent method for basic processing
        content_list, questionnaire_data = super().process_file(file_path)
        
        # Enhance the content list with additional metadata for questionnaires
        enhanced_content_list = []
        for content_item in content_list:
            if content_item:
                # Add additional context for better questionnaire generation
                enhanced_item = self._add_questionnaire_context(content_item)
                enhanced_content_list.append(enhanced_item)
        
        logger.info(f"Processed {len(enhanced_content_list)} content items with enhanced context")
        
        # Return the content list and questionnaire data
        return enhanced_content_list, questionnaire_data
    
    def _add_questionnaire_context(self, content_item: Dict[str, Any]) -> Dict[str, Any]:
        """Add context that helps with questionnaire generation."""
        if "metadata" not in content_item:
            content_item["metadata"] = {}
        
        # Add educational context for better question generation
        content_item["metadata"]["educational_context"] = {
            "content_purpose": self._determine_content_purpose(content_item),
            "learning_objectives": self._extract_learning_objectives(content_item),
            "question_types": self._suggest_question_types(content_item),
        }
        
        return content_item
    
    def _determine_content_purpose(self, content_item: Dict[str, Any]) -> str:
        """Determine the educational purpose of the content."""
        content_type = content_item.get("type", "generic")
        text_content = content_item.get("text", "") or content_item.get("enhanced_text", "")
        
        # Simple heuristics based on content type
        purpose_map = {
            "image": "visual explanation",
            "table": "data presentation",
            "equation": "mathematical concept",
            "generic": "information delivery"
        }
        
        return purpose_map.get(content_type, "information delivery")
    
    def _extract_learning_objectives(self, content_item: Dict[str, Any]) -> List[str]:
        """Extract or infer learning objectives from content."""
        # This would ideally use LLM analysis, but for now we'll use simple heuristics
        content_type = content_item.get("type", "generic")
        text_content = content_item.get("text", "") or content_item.get("enhanced_text", "")
        
        # Basic learning objectives based on content type
        objectives_map = {
            "image": ["Visual interpretation", "Diagram analysis"],
            "table": ["Data analysis", "Pattern recognition"],
            "equation": ["Mathematical understanding", "Problem solving"],
            "generic": ["Comprehension", "Knowledge recall"]
        }
        
        return objectives_map.get(content_type, ["Comprehension"])
    
    def _suggest_question_types(self, content_item: Dict[str, Any]) -> List[str]:
        """Suggest appropriate question types based on content."""
        content_type = content_item.get("type", "generic")
        
        # Question type suggestions based on content type
        question_types_map = {
            "image": ["Multiple choice", "Short answer", "Diagram labeling"],
            "table": ["Multiple choice", "Data interpretation", "Calculation"],
            "equation": ["Problem solving", "Derivation", "Application"],
            "generic": ["Multiple choice", "Short answer", "Essay"]
        }
        
        return question_types_map.get(content_type, ["Multiple choice", "Short answer"])