import os
import subprocess
import sys
from typing import List, Dict, Any, Optional
import logging
from pathlib import Path
from PIL import Image
import pytesseract
import fitz  # PyMuPDF for PDF analysis
import io
import re

from rag.config.settings import settings
from rag.utils.file_handler import FileHandler
from rag.utils.exceptions import FileProcessingError, UnsupportedFormatError, ParserError

# Import RAGAnything library
RAGANYTHING_AVAILABLE = False
RAGAnything = None
RAGAnythingConfig = None

try:
    from raganything import RAGAnything, RAGAnythingConfig
    RAGANYTHING_AVAILABLE = True
except ImportError:
    pass

# PDF image processing imports
try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

from logic.logging_config import configured_logger as logger

class DocumentParser:
    """
    Document parser for processing PDFs and images using MinerU/Docling.
    
    This parser handles multiple document formats and extracts structured content
    with metadata, coordinates, and content type classification. It supports:
    - PDF parsing with PyMuPDF fallback
    - Image parsing with OCR capabilities
    - Content type classification (text, table, equation, image)
    - Coordinate-based content positioning
    """
    
    def __init__(self):
        """
        Initialize the document parser with appropriate backend based on configuration.
        
        The parser attempts to use RAGAnything if available, otherwise falls back
        to PyMuPDF for PDF processing. Image processing uses PIL and pytesseract
        for OCR capabilities when enabled.
        """
        self.parser_type = settings.PARSER
        self.raganything = None
        self._initialize_parser()
    
    def _initialize_parser(self):
        """Initialize the appropriate parser based on configuration."""
        if self.parser_type == "raganything" and RAGANYTHING_AVAILABLE:
            try:
                config = RAGAnythingConfig(
                    model_name=settings.RAGANYTHING_MODEL,
                    max_pages=settings.MAX_PAGES,
                    chunk_size=settings.CHUNK_SIZE,
                    chunk_overlap=settings.CHUNK_OVERLAP
                )
                self.raganything = RAGAnything(config)
                logger.info("RAGAnything parser initialized")
            except Exception as e:
                logger.error(f"Failed to initialize RAGAnything: {e}")
                self.raganything = None
        elif self.parser_type == "pymupdf":
            logger.info("PyMuPDF parser initialized")
        else:
            logger.warning(f"Unknown parser type: {self.parser_type}, falling back to PyMuPDF")
            self.parser_type = "pymupdf"  # Set to valid fallback
    
    def parse_document(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Parse a document file and return structured content.
        
        This is the main entry point for document parsing. It determines the
        appropriate parsing method based on file extension:
        - PDF files: Processed with RAGAnything or PyMuPDF fallback
        - Image files: Processed with PIL and optional OCR
        
        Args:
            file_path: Path to the document file to parse
            
        Returns:
            List of content items with text, metadata, and coordinates.
            Each item contains:
            - type: Content type (text, table, equation, image)
            - text: Extracted text content
            - page: Page number (1-indexed)
            - coordinates: Position and dimensions
            - source_file: Original file path
            - confidence: Extraction confidence score (0.0-1.0)
            
        Raises:
            FileProcessingError: If file cannot be found or parsed
            UnsupportedFormatError: If file format is not supported
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileProcessingError(f"File not found: {file_path}")
        
        file_ext = file_path.suffix.lower()
        
        if file_ext == ".pdf":
            return self._parse_pdf(file_path)
        elif file_ext in [".png", ".jpg", ".jpeg", ".bmp", ".tiff"]:
            return self._parse_image(file_path)
        else:
            raise UnsupportedFormatError(f"Unsupported file format: {file_ext}")
    
    def _parse_pdf(self, pdf_path: Path) -> List[Dict[str, Any]]:
        """
        Parse PDF using RAGAnything or PyMuPDF fallback.
        
        This method selects the appropriate PDF parsing backend:
        - If RAGAnything is available and configured, uses advanced parsing
        - Otherwise falls back to PyMuPDF for basic text extraction
        
        Args:
            pdf_path: Path to the PDF file to parse
            
        Returns:
            List of content items with text, metadata, and coordinates
            
        Raises:
            ParserError: If PDF parsing fails
        """
        try:
            if self.raganything:
                # Use RAGAnything for advanced parsing with semantic understanding
                content = self.raganything.parse(str(pdf_path))
                return self._format_raganything_content(content)
            else:
                # Fallback to PyMuPDF for basic text extraction
                return self._parse_pdf_pymupdf(pdf_path)
        except Exception as e:
            logger.error(f"PDF parsing failed: {e}")
            raise ParserError(f"PDF parsing failed: {e}")
    
    def _parse_pdf_pymupdf(self, pdf_path: Path) -> List[Dict[str, Any]]:
        """
        Parse PDF using PyMuPDF with enhanced content classification.
        
        This method extracts text blocks and images from PDF pages, then:
        1. Classifies text content into semantic types (table, equation, etc.)
        2. Processes images with OCR when available
        3. Extracts coordinate information for spatial layout
        
        Args:
            pdf_path: Path to the PDF file to parse
            
        Returns:
            List of classified content items with text and metadata
            
        Raises:
            ParserError: If PyMuPDF parsing fails
        """
        content_items = []
        try:
            doc = fitz.open(str(pdf_path))
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                
                # Extract text blocks with positioning information
                text_blocks = page.get_text("blocks")
                
                # Extract images if pdf2image is available
                images = []
                if PDF2IMAGE_AVAILABLE:
                    try:
                        page_images = convert_from_path(str(pdf_path), first_page=page_num+1, last_page=page_num+1)
                        if page_images:
                            img = page_images[0]
                            img_bytes = io.BytesIO()
                            img.save(img_bytes, format='PNG')
                            images.append({
                                "data": img_bytes.getvalue(),
                                "mime_type": "image/png",
                                "page": page_num + 1,
                                "type": "image"
                            })
                    except Exception as e:
                        logger.warning(f"Failed to extract images from page {page_num + 1}: {e}")
                
                # Enhanced content classification for text blocks
                for block in text_blocks:
                    if isinstance(block[4], str) and len(block[4].strip()) > 0:  # Text block
                        text_content = block[4].strip()
                        content_type = self._classify_content_type(text_content)
                        
                        content_item = {
                            "type": content_type,
                            "text": text_content,
                            "page": page_num + 1,
                            "coordinates": {
                                "x": block[0],
                                "y": block[1],
                                "width": block[2] - block[0],
                                "height": block[3] - block[1]
                            },
                            "source_file": str(pdf_path),
                            "confidence": 1.0
                        }
                        content_items.append(content_item)
                
                # Add images with OCR if they're likely to contain text/diagrams
                for image in images:
                    # For image-based PDFs, we should process each image as a potential container
                    # of multiple content types (text, diagrams, equations, etc.)
                    image_content_items = self._process_image_page(image, page_num + 1, str(pdf_path))
                    content_items.extend(image_content_items)
            
            doc.close()
            logger.info(f"Parsed PDF {pdf_path} with {len(content_items)} content items")
            return content_items
            
        except Exception as e:
            logger.error(f"PyMuPDF parsing failed: {e}")
            raise ParserError(f"PyMuPDF parsing failed: {e}")

    def _classify_content_type(self, text: str) -> str:
        """
        Classify content type based on text characteristics.
        
        This method uses heuristic rules to determine the semantic type of content:
        - Tables: Detected by pipe characters and table-like structure
        - Equations: Detected by mathematical symbols and patterns
        - Generic text: Default fallback for unclassified content
        
        Args:
            text: Text content to classify
            
        Returns:
            Content type classification (table, equation, or generic)
        """
        text_lower = text.lower().strip()
        
        # Check for table-like patterns (multiple columns of data)
        if '|' in text and text.count('|') > 3:
            return "table"
        
        # Check for explicit table indicators
        if any(keyword in text_lower for keyword in ['table:', 'table-', 'tab:', 'tab-']):
            return "table"
        
        # Check for equation-like patterns (mathematical symbols)
        equation_patterns = ['=', '+', '-', '*', '/', '∫', '∑', '∏', '√', '^', '≤', '≥', '≠', '≈']
        if any(pattern in text for pattern in equation_patterns) and len(text) < 300:
            # Additional check for equation structure
            if re.search(r'[a-zA-Z][0-9]|[0-9][a-zA-Z]|[a-zA-Z]\s*=', text):
                return "equation"
        
        # Check for explicit equation indicators
        if any(keyword in text_lower for keyword in ['equation:', 'eq:', 'formula:', 'theorem:']):
            return "equation"
        
        # Check for mathematical expressions with typical equation patterns
        # TODO: Fix regex pattern for LaTeX math detection
        # Check for mathematical expressions with typical equation patterns
        # TODO: Implement LaTeX math detection
        pass

    def _process_image_page(self, image_data: Dict[str, Any], page_num: int, source_file: str) -> List[Dict[str, Any]]:
        """Process an image page that may contain multiple content types."""
        content_items = []
        
        # Add the image itself as a content item
        image_item = {
            "type": "image",
            "data": image_data["data"],
            "mime_type": image_data["mime_type"],
            "page": page_num,
            "source_file": source_file,
            "confidence": 1.0
        }
        content_items.append(image_item)
        
        # Try OCR to extract text content from the image
        if settings.ENABLE_OCR:
            try:
                img = Image.open(io.BytesIO(image_data["data"]))
                ocr_text = pytesseract.image_to_string(img)
                
                if ocr_text.strip():
                    # Split OCR text into potential content blocks
                    blocks = self._split_ocr_text_into_blocks(ocr_text)
                    for i, block in enumerate(blocks):
                        if block.strip():
                            content_type = self._classify_content_type(block)
                            content_items.append({
                                "type": content_type,
                                "text": block.strip(),
                                "page": page_num,
                                "source_file": source_file,
                                "confidence": 0.8,  # Lower confidence for OCR extracted content
                                "from_ocr": True,
                                "is_component": True  # Flag to indicate this is a component of the page
                            })
            except Exception as e:
                logger.warning(f"OCR processing failed for image on page {page_num}: {e}")
        
        return content_items

    def _split_ocr_text_into_blocks(self, ocr_text: str) -> List[str]:
        """Split OCR text into logical content blocks."""
        # Split by double newlines (paragraphs)
        paragraphs = ocr_text.split('\n\n')
        
        # Further split long paragraphs if they contain multiple sentences
        blocks = []
        for paragraph in paragraphs:
            if len(paragraph) > 500:  # If paragraph is very long
                sentences = re.split(r'[.!?]+\\s+', paragraph)
                current_block = ""
                for sentence in sentences:
                    if len(current_block) + len(sentence) < 400:
                        current_block += sentence + ". "
                    else:
                        if current_block:
                            blocks.append(current_block.strip())
                        current_block = sentence + ". "
                if current_block:
                    blocks.append(current_block.strip())
            else:
                blocks.append(paragraph)
        
        return blocks
    
    def _parse_image(self, image_path: Path) -> List[Dict[str, Any]]:
        """Parse image file with enhanced content extraction."""
        content_items = []
        try:
            with Image.open(image_path) as img:
                img_bytes = io.BytesIO()
                img.save(img_bytes, format='PNG')
                img_bytes = img_bytes.getvalue()
            
            # Add the image itself as a content item
            image_item = {
                "type": "image",
                "data": img_bytes,
                "mime_type": "image/png",
                "page": 1,
                "source_file": str(image_path),
                "confidence": 1.0
            }
            content_items.append(image_item)
            
            # Try OCR to extract text content from the image
            if settings.ENABLE_OCR:
                try:
                    text = pytesseract.image_to_string(img)
                    if text.strip():
                        # Split OCR text into potential content blocks
                        blocks = self._split_ocr_text_into_blocks(text)
                        for i, block in enumerate(blocks):
                            if block.strip():
                                content_type = self._classify_content_type(block)
                                content_items.append({
                                    "type": content_type,
                                    "text": block.strip(),
                                    "page": 1,
                                    "source_file": str(image_path),
                                    "confidence": 0.8,  # Lower confidence for OCR extracted content
                                    "from_ocr": True,
                                    "is_component": True  # Flag to indicate this is a component of the page
                                })
                except Exception as e:
                    logger.warning(f"OCR failed for {image_path}: {e}")
            
            logger.info(f"Parsed image {image_path} with {len(content_items)} content items")
            return content_items
            
        except Exception as e:
            logger.error(f"Image parsing failed: {e}")
            raise ParserError(f"Image parsing failed: {e}")
    
    def _format_raganything_content(self, rag_content: Any) -> List[Dict[str, Any]]:
        """Format RAGAnything output to standard content format."""
        if not RAGANYTHING_AVAILABLE:
            return []
        
        try:
            content_items = []
            # This would need to be implemented based on actual RAGAnything output format
            # For now, return empty list or basic structure
            logger.warning("RAGAnything content formatting not implemented yet")
            return content_items
        except Exception as e:
            logger.error(f"RAGAnything formatting failed: {e}")
            raise ParserError(f"RAGAnything formatting failed: {e}")
    
    def parse_directory(self, directory_path: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Parse all documents in a directory.
        
        Args:
            directory_path: Path to directory containing documents
            
        Returns:
            Dictionary mapping file paths to their parsed content
        """
        directory_path = Path(directory_path)
        if not directory_path.exists() or not directory_path.is_dir():
            raise FileProcessingError(f"Directory not found: {directory_path}")
        
        results = {}
        supported_extensions = {'.pdf', '.png', '.jpg', '.jpeg', '.bmp', '.tiff'}
        
        for file_path in directory_path.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                try:
                    content = self.parse_document(str(file_path))
                    results[str(file_path)] = content
                    logger.info(f"Parsed {file_path}: {len(content)} items")
                except Exception as e:
                    logger.error(f"Failed to parse {file_path}: {e}")
                    results[str(file_path)] = []
        
        # TODO: Fix regex pattern for LaTeX math detection
            return "equation"
        
        # TODO: Fix regex pattern for LaTeX display math detection

    def _process_image_page(self, image_data: Dict[str, Any], page_num: int, source_file: str) -> List[Dict[str, Any]]:
        """Process an image page that may contain multiple content types."""
        content_items = []
        
        # Add the image itself as a content item
        image_item = {
            "type": "image",
            "data": image_data["data"],
            "mime_type": image_data["mime_type"],
            "page": page_num,
            "source_file": source_file,
            "confidence": 1.0,
            "is_page_image": True  # Flag to indicate this is a full page image
        }
        content_items.append(image_item)
        
        # Try OCR to extract text content from the image
        if settings.ENABLE_OCR:
            try:
                img = Image.open(io.BytesIO(image_data["data"]))
                ocr_text = pytesseract.image_to_string(img)
                
                if ocr_text.strip():
                    # Split OCR text into potential content blocks
                    blocks = self._split_ocr_text_into_blocks(ocr_text)
                    for i, block in enumerate(blocks):
                        if block.strip():
                            content_type = self._classify_content_type(block)
                            content_items.append({
                                "type": content_type,
                                "text": block.strip(),
                                "page": page_num,
                                "source_file": source_file,
                                "confidence": 0.8,  # Lower confidence for OCR extracted content
                                "from_ocr": True,
                                "is_component": True  # Flag to indicate this is a component of the page
                            })
            except Exception as e:
                logger.warning(f"OCR processing failed for image on page {page_num}: {e}")
        
        return content_items

    def _split_ocr_text_into_blocks(self, ocr_text: str) -> List[str]:
        """Split OCR text into logical content blocks."""
        # Split by double newlines (paragraphs)
        paragraphs = ocr_text.split('\n\n')
        
        # Further split long paragraphs if they contain multiple sentences
        blocks = []
        for paragraph in paragraphs:
            if len(paragraph) > 500:  # If paragraph is very long
                sentences = re.split(r'[.!?]+\\s+', paragraph)
                current_block = ""
                for sentence in sentences:
                    if len(current_block) + len(sentence) < 400:
                        current_block += sentence + ". "
                    else:
                        if current_block:
                            blocks.append(current_block.strip())
                        current_block = sentence + ". "
                if current_block:
                    blocks.append(current_block.strip())
            else:
                blocks.append(paragraph)
        
        return blocks
    
    def _parse_image(self, image_path: Path) -> List[Dict[str, Any]]:
        """Parse image file with enhanced content extraction."""
        content_items = []
        try:
            with Image.open(image_path) as img:
                img_bytes = io.BytesIO()
                img.save(img_bytes, format='PNG')
                img_bytes = img_bytes.getvalue()
            
            # Add the image itself as a content item
            image_item = {
                "type": "image",
                "data": img_bytes,
                "mime_type": "image/png",
                "page": 1,
                "source_file": str(image_path),
                "confidence": 1.0,
                "is_page_image": True  # Flag to indicate this is a full page image
            }
            content_items.append(image_item)
            
            # Try OCR to extract text content from the image
            if settings.ENABLE_OCR:
                try:
                    text = pytesseract.image_to_string(img)
                    if text.strip():
                        # Split OCR text into potential content blocks
                        blocks = self._split_ocr_text_into_blocks(text)
                        for i, block in enumerate(blocks):
                            if block.strip():
                                content_type = self._classify_content_type(block)
                                content_items.append({
                                    "type": content_type,
                                    "text": block.strip(),
                                    "page": 1,
                                    "source_file": str(image_path),
                                    "confidence": 0.8,  # Lower confidence for OCR extracted content
                                    "from_ocr": True,
                                    "is_component": True  # Flag to indicate this is a component of the page
                                })
                except Exception as e:
                    logger.warning(f"OCR failed for {image_path}: {e}")
            
            logger.info(f"Parsed image {image_path} with {len(content_items)} content items")
            return content_items
            
        except Exception as e:
            logger.error(f"Image parsing failed: {e}")
            raise ParserError(f"Image parsing failed: {e}")
    
    def _format_raganything_content(self, rag_content: Any) -> List[Dict[str, Any]]:
        """Format RAGAnything output to standard content format."""
        if not RAGANYTHING_AVAILABLE:
            return []
        
        try:
            content_items = []
            # This would need to be implemented based on actual RAGAnything output format
            # For now, return empty list or basic structure
            logger.warning("RAGAnything content formatting not implemented yet")
            return content_items
        except Exception as e:
            logger.error(f"RAGAnything formatting failed: {e}")
            raise ParserError(f"RAGAnything formatting failed: {e}")
    
    def parse_directory(self, directory_path: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Parse all documents in a directory.
        
        Args:
            directory_path: Path to directory containing documents
            
        Returns:
            Dictionary mapping file paths to their parsed content
        """
        directory_path = Path(directory_path)
        if not directory_path.exists() or not directory_path.is_dir():
            raise FileProcessingError(f"Directory not found: {directory_path}")
        
        results = {}
        supported_extensions = {'.pdf', '.png', '.jpg', '.jpeg', '.bmp', '.tiff'}
        
        for file_path in directory_path.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                try:
                    content = self.parse_document(str(file_path))
                    results[str(file_path)] = content
                    logger.info(f"Parsed {file_path}: {len(content)} items")
                except Exception as e:
                    logger.error(f"Failed to parse {file_path}: {e}")
                    results[str(file_path)] = []
        
        # TODO: Fix regex pattern for LaTeX display math detection
            return "equation"
        
        # Default to text for everything else
        return "text"

    def _process_image_page(self, image_data: Dict[str, Any], page_num: int, source_file: str) -> List[Dict[str, Any]]:
        """
        Process an image page that may contain multiple content types.
        
        This method processes images that might contain various content types:
        1. Stores the image itself as a content item
        2. Applies OCR to extract text content when enabled
        3. Classifies OCR-extracted text into semantic types
        4. Preserves spatial relationships between content elements
        
        Args:
            image_data: Dictionary containing image bytes, MIME type, and metadata
            page_num: Page number (1-indexed)
            source_file: Path to the source file
            
        Returns:
            List of content items extracted from the image
        """
        content_items = []
        
        # Add the image itself as a content item
        image_item = {
            "type": "image",
            "data": image_data["data"],
            "mime_type": image_data["mime_type"],
            "page": page_num,
            "source_file": source_file,
            "confidence": 1.0,
            "is_page_image": True  # Flag to indicate this is a full page image
        }
        content_items.append(image_item)
        
        # Try OCR to extract text content from the image
        if settings.ENABLE_OCR:
            try:
                img = Image.open(io.BytesIO(image_data["data"]))
                ocr_text = pytesseract.image_to_string(img)
                
                if ocr_text.strip():
                    # Split OCR text into potential content blocks
                    blocks = self._split_ocr_text_into_blocks(ocr_text)
                    for i, block in enumerate(blocks):
                        if block.strip():
                            content_type = self._classify_content_type(block)
                            content_items.append({
                                "type": content_type,
                                "text": block.strip(),
                                "page": page_num,
                                "source_file": source_file,
                                "confidence": 0.8,  # Lower confidence for OCR extracted content
                                "from_ocr": True,
                                "is_component": True  # Flag to indicate this is a component of the page
                            })
            except Exception as e:
                logger.warning(f"OCR processing failed for image on page {page_num}: {e}")
        
        return content_items

    def _split_ocr_text_into_blocks(self, ocr_text: str) -> List[str]:
        """Split OCR text into logical content blocks."""
        # Split by double newlines (paragraphs)
        paragraphs = ocr_text.split('\n\n')
        
        # Further split long paragraphs if they contain multiple sentences
        blocks = []
        for paragraph in paragraphs:
            if len(paragraph) > 500:  # If paragraph is very long
                sentences = re.split(r'[.!?]+\\s+', paragraph)
                current_block = ""
                for sentence in sentences:
                    if len(current_block) + len(sentence) < 400:
                        current_block += sentence + ". "
                    else:
                        if current_block:
                            blocks.append(current_block.strip())
                        current_block = sentence + ". "
                if current_block:
                    blocks.append(current_block.strip())
            else:
                blocks.append(paragraph)
        
        return blocks
    
    def _parse_image(self, image_path: Path) -> List[Dict[str, Any]]:
        """Parse image file with enhanced content extraction."""
        content_items = []
        try:
            with Image.open(image_path) as img:
                img_bytes = io.BytesIO()
                img.save(img_bytes, format='PNG')
                img_bytes = img_bytes.getvalue()
            
            # Add the image itself as a content item
            image_item = {
                "type": "image",
                "data": img_bytes,
                "mime_type": "image/png",
                "page": 1,
                "source_file": str(image_path),
                "confidence": 1.0,
                "is_page_image": True  # Flag to indicate this is a full page image
            }
            content_items.append(image_item)
            
            # Try OCR to extract text content from the image
            if settings.ENABLE_OCR:
                try:
                    text = pytesseract.image_to_string(img)
                    if text.strip():
                        # Split OCR text into potential content blocks
                        blocks = self._split_ocr_text_into_blocks(text)
                        for i, block in enumerate(blocks):
                            if block.strip():
                                content_type = self._classify_content_type(block)
                                content_items.append({
                                    "type": content_type,
                                    "text": block.strip(),
                                    "page": 1,
                                    "source_file": str(image_path),
                                    "confidence": 0.8,  # Lower confidence for OCR extracted content
                                    "from_ocr": True,
                                    "is_component": True  # Flag to indicate this is a component of the page
                                })
                except Exception as e:
                    logger.warning(f"OCR failed for {image_path}: {e}")
            
            logger.info(f"Parsed image {image_path} with {len(content_items)} content items")
            return content_items
            
        except Exception as e:
            logger.error(f"Image parsing failed: {e}")
            raise ParserError(f"Image parsing failed: {e}")
    
    def _format_raganything_content(self, rag_content: Any) -> List[Dict[str, Any]]:
        """Format RAGAnything output to standard content format."""
        if not RAGANYTHING_AVAILABLE:
            return []
        
        try:
            content_items = []
            # This would need to be implemented based on actual RAGAnything output format
            # For now, return empty list or basic structure
            logger.warning("RAGAnything content formatting not implemented yet")
            return content_items
        except Exception as e:
            logger.error(f"RAGAnything formatting failed: {e}")
            raise ParserError(f"RAGAnything formatting failed: {e}")
    
    def parse_directory(self, directory_path: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Parse all documents in a directory.
        
        Args:
            directory_path: Path to directory containing documents
            
        Returns:
            Dictionary mapping file paths to their parsed content
        """
        directory_path = Path(directory_path)
        if not directory_path.exists() or not directory_path.is_dir():
            raise FileProcessingError(f"Directory not found: {directory_path}")
        
        results = {}
        supported_extensions = {'.pdf', '.png', '.jpg', '.jpeg', '.bmp', '.tiff'}
        
        for file_path in directory_path.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                try:
                    content = self.parse_document(str(file_path))
                    results[str(file_path)] = content
                    logger.info(f"Parsed {file_path}: {len(content)} items")
                except Exception as e:
                    logger.error(f"Failed to parse {file_path}: {e}")
                    results[str(file_path)] = []
        
        return results