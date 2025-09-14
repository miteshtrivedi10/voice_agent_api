import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv()


class Settings:
    # Working directory for RAG storage
    WORKING_DIR: str = os.getenv("WORKING_DIR", "./rag_storage")

    # Parser selection (pymupdf or raganything)
    PARSER: str = os.getenv("PARSER", "pymupdf")

    # Parsing method (auto, txt, ocr)
    PARSE_METHOD: str = os.getenv("PARSE_METHOD", "auto")

    # Enable/disable multimodal processing
    ENABLE_IMAGE_PROCESSING: bool = (
        os.getenv("ENABLE_IMAGE_PROCESSING", "true").lower() == "true"
    )
    ENABLE_TABLE_PROCESSING: bool = (
        os.getenv("ENABLE_TABLE_PROCESSING", "true").lower() == "true"
    )
    ENABLE_EQUATION_PROCESSING: bool = (
        os.getenv("ENABLE_EQUATION_PROCESSING", "true").lower() == "true"
    )

    # Context extraction configuration
    CONTEXT_WINDOW: int = int(os.getenv("CONTEXT_WINDOW", "1"))
    CONTEXT_MODE: str = os.getenv("CONTEXT_MODE", "page")
    MAX_CONTEXT_TOKENS: int = int(os.getenv("MAX_CONTEXT_TOKENS", "2000"))

    # Ollama integration settings
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_SONOMA_MODEL: str = os.getenv("OLLAMA_SONOMA_MODEL", "sonoma-dusk-alpha")
    OLLAMA_NOMIC_MODEL: str = os.getenv("OLLAMA_NOMIC_MODEL", "nomic-embed-text")

    # OpenRouter model settings
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "openrouter/sonoma-dusk-alpha")

    # Image-based PDF detection
    ENABLE_IMAGE_PDF_DETECTION: bool = (
        os.getenv("ENABLE_IMAGE_PDF_DETECTION", "true").lower() == "true"
    )

    # Semantic chunking parameters
    SEMANTIC_CHUNK_SIZE: int = int(os.getenv("SEMANTIC_CHUNK_SIZE", "1000"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "200"))
    PAGE_GROUPING_THRESHOLD: float = float(os.getenv("PAGE_GROUPING_THRESHOLD", "0.8"))

    # Milvus
    MILVUS_URI = os.getenv("MILVUS_URI", "localhost:19530")
    MILVUS_TOKEN = os.getenv("MILVUS_TOKEN", "Invalid Token")


    # OCR settings
    ENABLE_OCR: bool = (
        os.getenv("ENABLE_OCR", "false").lower() == "true"
    )

settings = Settings()
