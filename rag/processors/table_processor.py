from typing import List, Dict, Any, Optional, Callable
import logging
from .base_processor import BaseModalProcessor

logger = logging.getLogger(__name__)


class TableModalProcessor(BaseModalProcessor):
    """Processor for analyzing tabular data."""
    
    def __init__(self, model_func: Optional[Callable] = None):
        """
        Initialize the table modal processor.
        
        Args:
            model_func: Function to call the LLM for table analysis
        """
        super().__init__(model_func)
        if model_func is None:
            raise ValueError("model_func is required for TableModalProcessor. No fallback available.")
        self.model_func = model_func
    
    def generate_description_only(self, content_item: Dict[str, Any], context: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Generate a textual description of the table content without multimodal processing.
        
        Args:
            content_item: The table content item to process
            context: Optional context information from surrounding content
            
        Returns:
            Enhanced content item with description
        """
        # Create enhanced item
        enhanced_item = content_item.copy()
        
        # Extract basic information from the content item
        file_path = content_item.get("source", "unknown") or "unknown"
        page_number = content_item.get("page", "unknown") or "unknown"
        
        # Try to extract table-specific information
        table_data = content_item.get("table_data", {})
        rows = table_data.get("rows", [])
        headers = table_data.get("headers", [])
        
        # Create a basic description
        description = f"Table from {file_path}"
        if page_number != "unknown":
            description += f", page {page_number}"
            
        # Add information about table size if available
        if headers:
            description += f" with {len(headers)} columns"
        if rows:
            description += f" and {len(rows)} rows"
            
        # Add context information if available
        if context:
            context_info = self.extract_context_aware_metadata(content_item, context)
            if "chapter" in context_info:
                description += f", in {context_info['chapter']}"
        
        # Add the description to the enhanced item
        enhanced_item["enhanced_text"] = description
        enhanced_item["description"] = description
        enhanced_item["processed_by"] = "TableModalProcessor"
        
        return enhanced_item
    
    def process_multimodal_content(self, content_item: Dict[str, Any], context: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Process the table content with full multimodal capabilities.
        
        Args:
            content_item: The table content item to process
            context: Optional context information from surrounding content
            
        Returns:
            Processed table content with enhanced metadata and analysis
        """
        # Extract context-aware metadata
        metadata = self.extract_context_aware_metadata(content_item, context)
        
        # Add table-specific metadata
        metadata["processing_type"] = "multimodal"
        metadata["processor"] = "TableModalProcessor"
        
        # Process the table with the model
        try:
            table_analysis = self._analyze_table(content_item, context)
            metadata["table_analysis"] = table_analysis
            metadata["has_table_analysis"] = True
        except Exception as e:
            logger.error(f"Error processing table with model: {e}")
            metadata["table_analysis"] = "Table analysis failed"
            metadata["has_table_analysis"] = False
            metadata["error"] = str(e)
        
        # Create the processed content item
        processed_item = content_item.copy()
        processed_item["metadata"] = metadata
        
        # Add enhanced text description if not already present
        if "enhanced_text" not in processed_item:
            processed_item["enhanced_text"] = self._generate_enhanced_description(content_item, metadata)
            
        return processed_item
    
    def _analyze_table(self, content_item: Dict[str, Any], context: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Analyze the table using the configured model function.
        
        Args:
            content_item: The table content item to process
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
        base_description = content_item.get("text", "Table content")
        
        if metadata.get("has_table_analysis", False):
            table_analysis = metadata.get("table_analysis", {})
            if isinstance(table_analysis, dict):
                summary = table_analysis.get("summary", "")
                educational_value = table_analysis.get("educational_value", "")
                
                parts = [base_description]
                if summary:
                    parts.append(summary)
                if educational_value:
                    parts.append(f"Educational value: {educational_value}")
                
                return ". ".join(parts)
        
        # If we have table data, provide a basic description
        table_data = content_item.get("table_data", {})
        if table_data:
            headers = table_data.get("headers", [])
            rows = table_data.get("rows", [])
            return f"Table with {len(headers)} columns and {len(rows)} rows containing {base_description}"
        
        return base_description
