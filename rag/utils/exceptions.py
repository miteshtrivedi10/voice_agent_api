class RAGAnythingError(Exception):
    """Base exception class for RAG-Anything errors."""
    pass

class FileProcessingError(RAGAnythingError):
    """Raised when there's an error processing a file."""
    def __init__(self, message: str, file_path: str = None):
        self.file_path = file_path
        super().__init__(message)

class UnsupportedFormatError(RAGAnythingError):
    """Raised when a file format is not supported."""
    def __init__(self, file_path: str, format: str):
        self.file_path = file_path
        self.format = format
        super().__init__(f"Unsupported file format '{format}' for file '{file_path}'")

class ParserError(RAGAnythingError):
    """Raised when there's an error with the document parser."""
    def __init__(self, message: str, parser: str = None):
        self.parser = parser
        super().__init__(message)
