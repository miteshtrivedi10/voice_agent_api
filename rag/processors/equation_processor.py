from typing import List, Dict, Any, Optional, Callable
from .base_processor import BaseModalProcessor
from logic.logging_config import configured_logger as logger


class EquationModalProcessor(BaseModalProcessor):
    """Processor for analyzing mathematical equations and expressions."""
    
    def __init__(self, model_func: Optional[Callable] = None):
        """
        Initialize the equation modal processor.
        
        Args:
            model_func: Function to call the LLM for equation analysis
        """
        super().__init__(model_func)
        if model_func is None:
            raise ValueError("model_func is required for EquationModalProcessor. No fallback available.")
        self.model_func = model_func
    
    def generate_description_only(self, content_item: Dict[str, Any], context: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Generate a textual description of the equation content without multimodal processing.
        
        Args:
            content_item: The equation content item to process
            context: Optional context information from surrounding content
            
        Returns:
            Enhanced content item with description
        """
        # Create enhanced item
        enhanced_item = content_item.copy()
        
        # Extract basic information from the content item
        file_path = content_item.get("source", "unknown") or "unknown"
        page_number = content_item.get("page", "unknown") or "unknown"
        equation_type = content_item.get("equation_type", "mathematical expression") or "mathematical expression"
        
        # Ensure equation_type is a string before calling capitalize
        if equation_type is None:
            equation_type = "mathematical expression"
        
        # Create a basic description
        description = f"{str(equation_type).capitalize()} from {file_path}"
        if page_number != "unknown":
            description += f", page {page_number}"
            
        # Add a snippet of the equation if available
        equation_text = content_item.get("text", "")
        if equation_text:
            # Truncate long equations for readability
            snippet = equation_text[:50] + "..." if len(equation_text) > 50 else equation_text
            description += f": {snippet}"
            
        # Add context information if available
        if context:
            context_info = self.extract_context_aware_metadata(content_item, context)
            if "chapter" in context_info:
                description += f", in {context_info['chapter']}"
        
        # Add the description to the enhanced item
        enhanced_item["enhanced_text"] = description
        enhanced_item["description"] = description
        enhanced_item["processed_by"] = "EquationModalProcessor"
        
        return enhanced_item
    
    def process_multimodal_content(self, content_item: Dict[str, Any], context: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Process the equation content with full multimodal capabilities.
        
        Args:
            content_item: The equation content item to process
            context: Optional context information from surrounding content
            
        Returns:
            Processed equation content with enhanced metadata and analysis
        """
        # Extract context-aware metadata
        metadata = self.extract_context_aware_metadata(content_item, context)
        
        # Add equation-specific metadata
        metadata["processing_type"] = "multimodal"
        metadata["processor"] = "EquationModalProcessor"
        
        # Process the equation with the model
        try:
            equation_analysis = self._analyze_equation(content_item, context)
            metadata["equation_analysis"] = equation_analysis
            metadata["has_equation_analysis"] = True
        except Exception as e:
            logger.error(f"Error processing equation with model: {e}")
            metadata["equation_analysis"] = "Equation analysis failed"
            metadata["has_equation_analysis"] = False
            metadata["error"] = str(e)
        
        # Create the processed content item
        processed_item = content_item.copy()
        processed_item["metadata"] = metadata
        
        # Add enhanced text description if not already present
        if "enhanced_text" not in processed_item:
            processed_item["enhanced_text"] = self._generate_enhanced_description(content_item, metadata)
            
        return processed_item
    
    def _analyze_equation(self, content_item: Dict[str, Any], context: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Analyze the equation using the configured model function.
        
        Args:
            content_item: The equation content item to process
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
        base_description = content_item.get("text", "Equation content")
        
        if metadata.get("has_equation_analysis", False):
            equation_analysis = metadata.get("equation_analysis", {})
            if isinstance(equation_analysis, dict):
                meaning = equation_analysis.get("meaning", "")
                application = equation_analysis.get("application", "")
                
                parts = [base_description]
                if meaning:
                    parts.append(f"Meaning: {meaning}")
                if application:
                    parts.append(f"Application: {application}")
                
                return ". ".join(parts)
        
        # Provide a basic description for equations
        equation_type = content_item.get("equation_type", "mathematical expression")
        return f"{equation_type}: {base_description}"