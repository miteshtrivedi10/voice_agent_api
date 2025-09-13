from typing import List, Dict, Any, Optional, Callable
import logging
from .base_processor import BaseModalProcessor

logger = logging.getLogger(__name__)


class GenericModalProcessor(BaseModalProcessor):
    """Processor for generic content types that don't have specialized processors."""
    
    def __init__(self, model_func: Optional[Callable] = None):
        """
        Initialize the generic modal processor.
        
        Args:
            model_func: Function to call the LLM for content analysis
        """
        super().__init__(model_func)
        if model_func is None:
            raise ValueError("model_func is required for GenericModalProcessor. No fallback available.")
        self.model_func = model_func
    
    def generate_description_only(self, content_item: Dict[str, Any], context: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Generate a textual description of the generic content without multimodal processing.
        
        Args:
            content_item: The content item to process
            context: Optional context information from surrounding content
            
        Returns:
            Enhanced content item with description
        """
        # Create enhanced item
        enhanced_item = content_item.copy()
        
        # Extract basic information from the content item
        file_path = content_item.get("source", "unknown") or "unknown"
        page_number = content_item.get("page", "unknown") or "unknown"
        content_type = content_item.get("type", "content") or "content"
        
        # Ensure content_type is a string before calling capitalize
        if content_type is None:
            content_type = "content"
        
        # Create a basic description
        description = f"{str(content_type).capitalize()} from {file_path}"
        if page_number != "unknown":
            description += f", page {page_number}"
            
        # Add a snippet of the content if available
        content_text = content_item.get("text", "")
        if content_text:
            # Truncate long content for readability
            snippet = content_text[:50] + "..." if len(content_text) > 50 else content_text
            description += f": {snippet}"
            
        # Add context information if available
        if context:
            context_info = self.extract_context_aware_metadata(content_item, context)
            if "chapter" in context_info:
                description += f", in {context_info['chapter']}"
        
        # Add the description to the enhanced item
        enhanced_item["enhanced_text"] = description
        enhanced_item["description"] = description
        enhanced_item["processed_by"] = "GenericModalProcessor"
        
        return enhanced_item
    
    def process_multimodal_content(self, content_item: Dict[str, Any], context: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Process the generic content with full multimodal capabilities.
        
        Args:
            content_item: The content item to process
            context: Optional context information from surrounding content
            
        Returns:
            Processed content with enhanced metadata and analysis
        """
        # Extract context-aware metadata
        metadata = self.extract_context_aware_metadata(content_item, context)
        
        # Add generic-specific metadata
        metadata["processing_type"] = "multimodal"
        metadata["processor"] = "GenericModalProcessor"
        
        # Process the content with the model
        try:
            content_analysis = self._analyze_content(content_item, context)
            metadata["content_analysis"] = content_analysis
            metadata["has_content_analysis"] = True
        except Exception as e:
            logger.error(f"Error processing content with model: {e}")
            metadata["content_analysis"] = "Content analysis failed"
            metadata["has_content_analysis"] = False
            metadata["error"] = str(e)
        
        # Create the processed content item
        processed_item = content_item.copy()
        processed_item["metadata"] = metadata
        
        # Add enhanced text description if not already present
        if "enhanced_text" not in processed_item:
            processed_item["enhanced_text"] = self._generate_enhanced_description(content_item, metadata)
            
        return processed_item
    
    def _analyze_content(self, content_item: Dict[str, Any], context: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Analyze the content using the configured model function.
        
        Args:
            content_item: The content item to process
            context: Optional context information from surrounding content
            
        Returns:
            Analysis results from the model
        """
        return self.model_func(content_item, context)
    
    
    def _generate_enhanced_description(self, content_item: Dict[str, Any], metadata: Dict[str, Any]) -> str:
        """
        Generate an enhanced textual description based on the analysis.
        
        Args:
            content_item: The original content item
            metadata: The processed metadata
            
        Returns:
            Enhanced textual description
        """
        base_description = content_item.get("text", "Content")
        
        if metadata.get("has_content_analysis", False):
            content_analysis = metadata.get("content_analysis", {})
            if isinstance(content_analysis, dict):
                summary = content_analysis.get("summary", "")
                if summary:
                    return f"{base_description}. {summary}"
        
        return base_description