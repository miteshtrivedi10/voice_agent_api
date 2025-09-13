import pytest
import numpy as np
from rag.rag.storage import MockMilvusStorage

class TestMilvusBatchInsertion:
    """Test cases for Milvus batch insertion functionality."""
    
    def test_empty_batch(self):
        """Test inserting an empty batch."""
        storage = MockMilvusStorage()
        doc_ids = storage.insert_batch([])
        assert len(doc_ids) == 0
        stats = storage.get_collection_stats()
        assert stats["total_documents"] == 0
    
    def test_exact_batch_size(self):
        """Test inserting exactly 100 items (batch size)."""
        storage = MockMilvusStorage()
        test_data = [
            {
                "embedding": np.random.rand(768).tolist(),
                "text_content": f"Test content item {i}",
                "content_type": "text",
                "source_file": "test_file.txt",
                "page_id": "1",
                "metadata": {"test": f"metadata_{i}"},
                "processing_timestamp": "2025-01-01 00:00:00"
            }
            for i in range(100)
        ]
        
        doc_ids = storage.insert_batch(test_data)
        assert len(doc_ids) == 100
        stats = storage.get_collection_stats()
        assert stats["total_documents"] == 100
    
    def test_small_batch(self):
        """Test inserting fewer than batch size items (the problematic case)."""
        storage = MockMilvusStorage()
        test_data = [
            {
                "embedding": np.random.rand(768).tolist(),
                "text_content": f"Test content item {i}",
                "content_type": "text",
                "source_file": "test_file.txt",
                "page_id": "1",
                "metadata": {"test": f"metadata_{i}"},
                "processing_timestamp": "2025-01-01 00:00:00"
            }
            for i in range(6)  # The exact case that was failing
        ]
        
        doc_ids = storage.insert_batch(test_data)
        assert len(doc_ids) == 6
        stats = storage.get_collection_stats()
        assert stats["total_documents"] == 6
    
    def test_multiple_batches(self):
        """Test inserting data that spans multiple batches."""
        storage = MockMilvusStorage()
        # 250 items = 2 full batches + 1 partial batch
        test_data = [
            {
                "embedding": np.random.rand(768).tolist(),
                "text_content": f"Test content item {i}",
                "content_type": "text",
                "source_file": "test_file.txt",
                "page_id": str(i // 50 + 1),  # Different page for each batch
                "metadata": {"test": f"metadata_{i}"},
                "processing_timestamp": "2025-01-01 00:00:00"
            }
            for i in range(250)
        ]
        
        doc_ids = storage.insert_batch(test_data)
        assert len(doc_ids) == 250
        stats = storage.get_collection_stats()
        assert stats["total_documents"] == 250