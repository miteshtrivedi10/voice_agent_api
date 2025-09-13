from typing import List, Dict, Any, Optional
import logging
from .base_processor import BaseModalProcessor

logger = logging.getLogger(__name__)


class ImageModalProcessor(BaseModalProcessor):
    """Processor for detailed visual analysis of images."""
    
    def __init__(self, vision_model_func=None):
        """
        Initialize the image modal processor.
        
        Args:
            vision_model_func: Function to call the vision model for image analysis
        """
        super().__init__(vision_model_func)
        if vision_model_func is None:
            raise ValueError("vision_model_func is required for ImageModalProcessor. No fallback available.")
        self.vision_model_func = vision_model_func
    
    def generate_description_only(self, content_item: Dict[str, Any], context: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Generate a textual description of the image content without multimodal processing.
        
        Args:
            content_item: The image content item to process
            context: Optional context information from surrounding content
            
        Returns:
            Enhanced content item with description
        """
        # Create enhanced item
        enhanced_item = content_item.copy()
        
        # Remove binary data to avoid issues with embedding generation
        if "data" in enhanced_item:
            del enhanced_item["data"]
        
        # Extract basic information from the content item
        file_path = content_item.get("source_file", "unknown")
        page_number = content_item.get("page", "unknown")
        
        # Create a basic description based on available metadata
        description = f"Image from {file_path}"
        if page_number != "unknown":
            description += f", page {page_number}"
            
        # Add context information if available
        if context:
            context_info = self.extract_context_aware_metadata(content_item, context)
            if "chapter" in context_info:
                description += f", in {context_info['chapter']}"
        
        # Add the description to the enhanced item
        enhanced_item["enhanced_text"] = description
        enhanced_item["description"] = description
        enhanced_item["processed_by"] = "ImageModalProcessor"
        
        # If we have text content from OCR or other sources, use that as enhanced text
        if content_item.get("text"):
            enhanced_item["enhanced_text"] = content_item["text"]
        
        return enhanced_item
    
    def process_multimodal_content(self, content_item: Dict[str, Any], context: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Process the image content with full multimodal capabilities using vision models.
        
        Args:
            content_item: The image content item to process
            context: Optional context information from surrounding content
            
        Returns:
            Processed image content with enhanced metadata and analysis
        """
        # Create a copy of the content item and remove binary data
        processed_item = content_item.copy()
        if "data" in processed_item:
            del processed_item["data"]
        
        # Extract context-aware metadata
        metadata = self.extract_context_aware_metadata(content_item, context)
        
        # Add image-specific metadata
        metadata["processing_type"] = "multimodal"
        metadata["processor"] = "ImageModalProcessor"
        
        # Preserve our custom flags in metadata
        if content_item.get("is_page_image"):
            metadata["is_page_image"] = True
        if content_item.get("is_component"):
            metadata["is_component"] = True
        if content_item.get("from_ocr"):
            metadata["from_ocr"] = True
        
        # Process the image with the vision model
        try:
            visual_analysis = self.vision_model_func(content_item, context)
            metadata["visual_analysis"] = visual_analysis
            metadata["has_visual_analysis"] = True
            
            # Extract specific content types from visual analysis
            if isinstance(visual_analysis, dict):
                # Check if the image contains text, tables, or equations
                text_elements = visual_analysis.get("text_elements", [])
                objects_detected = visual_analysis.get("objects_detected", [])
                
                # Look for table-like structures
                if any("table" in obj.lower() for obj in objects_detected):
                    metadata["contains_table"] = True
                
                # Look for equation-like structures
                if any("equation" in obj.lower() or "formula" in obj.lower() for obj in objects_detected):
                    metadata["contains_equation"] = True
                
                # Look for diagram/chart structures
                if any("diagram" in obj.lower() or "chart" in obj.lower() or "graph" in obj.lower() for obj in objects_detected):
                    metadata["contains_diagram"] = True
        except Exception as e:
            logger.error(f"Error processing image with vision model: {e}")
            metadata["visual_analysis"] = "Visual analysis failed"
            metadata["has_visual_analysis"] = False
            metadata["error"] = str(e)
        
        # Add metadata to the processed item
        processed_item["metadata"] = metadata
        
        # Add enhanced text description if not already present
        if "enhanced_text" not in processed_item:
            processed_item["enhanced_text"] = self._generate_enhanced_description(content_item, metadata)
            
        return processed_item
    
    
    def _generate_enhanced_description(self, content_item: Dict[str, Any], metadata: Dict[str, Any]) -> str:
        """
        Generate an enhanced textual description based on the analysis.
        
        Args:
            content_item: The original content item
            metadata: The processed metadata
            
        Returns:
            Enhanced textual description
        """
        # Try to get text content from the original item first
        base_description = content_item.get("text", "")
        
        # If we have visual analysis, use that
        if metadata.get("has_visual_analysis", False):
            visual_analysis = metadata.get("visual_analysis", {})
            if isinstance(visual_analysis, dict):
                # Get description from visual analysis
                description = visual_analysis.get("description", "")
                scene_type = visual_analysis.get("scene_type", "image")
                educational_concept = visual_analysis.get("educational_concept", "")
                
                # Build a comprehensive description
                parts = []
                if scene_type and scene_type != "image":
                    parts.append(f"This {scene_type}")
                else:
                    parts.append("This image")
                
                if description:
                    parts.append(f"shows {description.lower()}")
                
                if educational_concept:
                    parts.append(f"related to {educational_concept.lower()}")
                
                return " ".join(parts)
        
        # If we have OCR text, use that
        if base_description:
            # If this is OCR text, indicate that
            if content_item.get("from_ocr"):
                return f"Text extracted from image: {base_description}"
            return base_description
        
        # Fallback to basic description
        file_path = content_item.get("source_file", "unknown")
        page_number = content_item.get("page", "unknown")
        return f"Image from {file_path}, page {page_number}"