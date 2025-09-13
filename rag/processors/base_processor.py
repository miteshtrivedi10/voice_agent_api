from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class BaseModalProcessor(ABC):
    """Base class for all modal processors."""
    
    def __init__(self, model_func=None):
        """
        Initialize the base modal processor.
        
        Args:
            model_func: Function to call the LLM or embedding model
        """
        self.model_func = model_func
    
    @abstractmethod
    def generate_description_only(self, content_item: Dict[str, Any], context: Optional[List[Dict[str, Any]]] = None) -> str:
        """
        Generate a textual description of the content item without multimodal processing.
        
        Args:
            content_item: The content item to process
            context: Optional context information from surrounding content
            
        Returns:
            A textual description of the content item
        """
        pass
    
    @abstractmethod
    def process_multimodal_content(self, content_item: Dict[str, Any], context: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Process the content item with full multimodal capabilities.
        
        Args:
            content_item: The content item to process
            context: Optional context information from surrounding content
            
        Returns:
            Processed content with enhanced metadata and analysis
        """
        pass
    
    def extract_context_aware_metadata(self, content_item: Dict[str, Any], context: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Extract metadata that takes context into account.
        
        Args:
            content_item: The content item to process
            context: Optional context information from surrounding content
            
        Returns:
            Context-aware metadata
        """
        metadata = content_item.get("metadata", {}).copy()
        
        # Add context-aware fields
        if context:
            metadata["context_window_size"] = len(context)
            metadata["has_contextual_information"] = True
            
            # Extract chapter/section information from context if available
            chapter_info = self._extract_chapter_info_from_context(context)
            if chapter_info:
                metadata["chapter"] = chapter_info
                
            # Extract document structure information
            structure_info = self._extract_structure_info_from_context(context)
            if structure_info:
                metadata["document_structure"] = structure_info
        else:
            metadata["has_contextual_information"] = False
            
        return metadata
    
    def _extract_chapter_info_from_context(self, context: List[Dict[str, Any]]) -> Optional[str]:
        """
        Extract chapter information from context.
        
        Args:
            context: Context information from surrounding content
            
        Returns:
            Chapter information if found, None otherwise
        """
        # Look for chapter information in the context
        for item in context:
            text = item.get("text", "")
            # Simple pattern matching for chapter information
            if "chapter" in text.lower() or "section" in text.lower():
                # Extract the first line that might contain chapter info
                lines = text.split("\n")
                for line in lines:
                    if "chapter" in line.lower() or "section" in line.lower():
                        return line.strip()
        return None
    
    def _extract_structure_info_from_context(self, context: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Extract document structure information from context.
        
        Args:
            context: Context information from surrounding content
            
        Returns:
            Document structure information if found, None otherwise
        """
        structure_info = {}
        
        # Count different content types in context
        content_types = {}
        for item in context:
            content_type = item.get("type", "unknown")
            content_types[content_type] = content_types.get(content_type, 0) + 1
            
        structure_info["content_type_distribution"] = content_types
        structure_info["context_size"] = len(context)
        
        return structure_info if content_types else None