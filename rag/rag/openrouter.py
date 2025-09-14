import os
import asyncio
import aiohttp
import requests
import json
import base64
import httpx
from typing import List, Dict, Any, Optional, Union
import numpy as np
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from rag.config.settings import settings
from .embedding import BaseEmbeddingGenerator
from logic.logging_config import configured_logger as logger


class OpenRouterClient:
    """Production-ready client for OpenRouter API with async support, retries, and multimodal capabilities."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 60,
        max_retries: int = 3,
        max_concurrent: int = 5,
        request_delay: float = 1.0,
    ):
        """
        Initialize the OpenRouter client with production-grade configuration.

        Args:
            api_key: OpenRouter API key (defaults to OPENROUTER_API_KEY environment variable)
            base_url: Base URL for OpenRouter API (defaults to production)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts for failed requests
            max_concurrent: Maximum concurrent async requests (semaphore limit)
            request_delay: Minimum delay between requests for rate limiting
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.api_base_url = base_url or "https://openrouter.ai/api/v1"
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_retries = max_retries
        self.session = None
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.request_delay = request_delay
        self.last_request_time = 0

        if not self.api_key:
            logger.warning("OpenRouter API key not provided. API calls will not work.")

        # High-accuracy prompts optimized for educational RAG processing with the configured model
        self.EDUCATIONAL_PROMPTS = {
            "image_multimodal_analysis": """You are an expert educational content analyst using the configured model for RAG processing. Analyze this textbook image with high precision.

Context from surrounding content: {context}

Provide comprehensive, structured analysis focusing on:
- Primary educational concepts and learning objectives (science, math, history, etc.)
- Content type classification (text, diagram, flowchart, chart, table, equation, photograph, illustration)
- Spatial organization and layout (top-to-bottom, left-to-right, grid, hierarchical)
- Extractable text content, labels, captions, and mathematical expressions
- Semantic relationships between visual and textual elements
- Educational value, complexity level, and RAG utility

Return ONLY valid JSON with this exact structure. Ensure all fields are populated and confidence scores are accurate:

{{
  "description": "Detailed 3-5 sentence description of educational content (150-250 words, academic tone)",
  "primary_content_type": "text_paragraph|heading|diagram|flowchart|chart_graph|table|equation_formula|photograph|illustration_drawing|caption|mixed_content|other",
  "confidence": 0.95,
  "secondary_types": ["array of 0-3 additional content types detected"],
  "educational_domain": "science|biology|physics|chemistry|math|algebra|geometry|calculus|history|geography|literature|language_arts|general|other",
  "educational_concepts": ["3-5 key learning objectives or topics with brief 1-sentence explanations"],
  "spatial_layout": {{
    "overall_structure": "sequential|hierarchical|comparative|spatial_relationship|temporal_sequence|single_element",
    "reading_direction": "left_to_right|top_to_bottom|center_outward|other",
    "regions": [
      {{
        "id": "region_1",
        "type": "text|visual|equation|table|header|footer|caption|legend",
        "position": "top|middle|bottom|left|center|right|full_page|top_left|top_right|bottom_left|bottom_right",
        "estimated_area_percent": 15,
        "estimated_coords": {{"x_percent": 10, "y_percent": 5, "width_percent": 80, "height_percent": 20}},
        "description": "brief 1-2 sentence analysis of region content",
        "confidence": 0.85,
        "content_summary": "key text or 3-5 main visual elements",
        "relations": ["connects_to_diagram", "explains_equation", "supports_table", "caption_for_image"]
      }}
    ]
  }},
  "relationships": [
    {{
      "source_id": "region_1_id_or_type",
      "source_type": "text|visual|equation|table",
      "target_id": "region_2_id_or_type",
      "target_type": "text|visual|equation|table",
      "relation_type": "describes|illustrates|supports|contains|references|demonstrates|complements|contrasts|sequences|defines",
      "direction": "text_to_visual|visual_to_text|element_to_element|bidirectional",
      "strength": 0.9,
      "educational_value": "high|medium|low",
      "rationale": "1-sentence explanation of why this relationship exists educationally"
    }}
  ],
  "extractable_text": "all readable text content including labels, captions, headers (max 1000 chars) or empty string",
  "math_content": {{
    "has_equations": true,
    "equation_count": 2,
    "symbols_detected": ["∫", "∑", "√", "∂", "×", "÷", "≈", "≤", "≥", "matrix", "vector"],
    "latex_potential": 0.8,
    "complexity": "simple|intermediate|advanced"
  }},
  "table_content": {{
    "has_tables": false,
    "table_count": 0,
    "structure_type": "simple|complex|hierarchical",
    "estimated_data_rows": 0
  }},
  "quality_assessment": {{
    "visual_clarity": "high|medium|low",
    "text_readability": "high|medium|low|none",
    "educational_complexity": "beginner|intermediate|advanced|expert",
    "rag_utility_score": 9.2,
    "processing_recommendations": ["ocr_enhancement", "region_segmentation", "multimodal_refinement"]
  }},
  "processing_metadata": {{
    "analysis_timestamp": "{timestamp}",
    "model_version": "configured-model",
    "input_quality": "high"
  }}
}}""",
            "content_classification": """Classify educational content type with high accuracy for RAG processing using the configured model.

Input content: {content}
Surrounding context: {context}

Classification categories (choose exactly one primary type):
- text_paragraph: Continuous prose or explanation
- heading_title: Section headers, chapter titles
- diagram: Scientific/technical drawings, flowcharts, schematics
- chart_graph: Bar/line/pie charts, graphs, plots
- table: Structured tabular data
- equation_formula: Mathematical expressions, formulas
- photograph: Real-world images, photos
- illustration_drawing: Artistic or conceptual drawings
- caption_label: Image captions, figure labels, annotations
- mixed_content: Multiple types in single element
- other: Cannot classify

Secondary types: 0-3 additional types if mixed content

Return ONLY valid JSON with precise classification:
{{
  "primary_type": "exact_category_from_list_above",
  "confidence": 0.95,
  "secondary_types": ["type1", "type2", "type3"],
  "structure_analysis": {{
    "is_compound": false,
    "component_count": 1,
    "layout_type": "single_block|multi_region|layered"
  }},
  "educational_domain": "science|biology|physics|chemistry|math|algebra|geometry|calculus|history|geography|literature|language_arts|social_studies|general_knowledge|other",
  "content_characteristics": {{
    "text_density": "low|medium|high|none",
    "visual_elements": 0,
    "mathematical_content": "none|simple|moderate|complex",
    "data_structured": false
  }},
  "processing_recommendation": "direct_text_extraction|ocr_required|multimodal_analysis|table_parsing|equation_recognition|skip_low_value",
  "rag_value": "high|medium|low"
}}""",
            "semantic_summarization": """Create high-quality semantic summary for RAG processing using the configured model.

Source content: {content}
Document context: {context}

Requirements for RAG optimization:
1. Preserve semantic meaning and educational intent
2. Extract key concepts, definitions, relationships
3. Maintain logical structure and flow
4. Identify important examples, formulas, data points
5. Highlight cross-references and dependencies
6. Ensure factual accuracy and academic tone

Structure the summary to maximize retrieval effectiveness:
- Lead with primary learning objective
- Follow with supporting concepts in logical order  
- Include quantitative data, formulas, key terms
- End with connections to broader context

Return ONLY valid JSON with comprehensive structure:
{{
  "semantic_summary": "concise yet comprehensive 150-300 word summary (academic tone, preserves structure)",
  "primary_learning_objective": "1-sentence statement of main educational goal",
  "key_concepts": ["array of 3-7 core concepts with 1-sentence explanations each"],
  "supporting_details": ["bullet points of important examples, formulas, data (max 10 items)"],
  "cross_references": ["connections to other topics/sections in document"],
  "educational_level": "beginner|intermediate|advanced|expert",
  "rag_optimization_score": 8.5,
  "preserved_structure": ["heading", "paragraph", "list", "table_reference", "equation"],
  "factual_accuracy": "high|medium|low",
  "summary_length_chars": 250,
  "processing_metadata": {{
    "timestamp": "{timestamp}",
    "model": "configured-model",
    "input_tokens": 0,
    "output_tokens": 0
  }}
}}""",
        }



    def chat_completion(self, model: str, messages: List[Dict[str, Any]],
                        max_tokens: int = 1000, temperature: float = 0.7) -> Dict[str, Any]:
        """Synchronous chat completion using OpenRouter API."""
        if not self.api_key:
            raise ValueError("OpenRouter API key is required for chat completions")
        
        url = f"{self.api_base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://rag-anything.com",
            "X-Title": "RAG-Anything"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        try:
            response = httpx.post(url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenRouter HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Chat completion error: {e}")
            raise