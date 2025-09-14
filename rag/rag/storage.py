import os
import json
import uuid
import time
from typing import List, Dict, Any, Optional, Union
import numpy as np
from pydantic import BaseModel, validator, Field
from pymilvus import MilvusClient, DataType, CollectionSchema, FieldSchema, IndexType
from pymilvus.milvus_client.index import IndexParams
from rag.config.settings import settings
from rag.utils.exceptions import FileProcessingError
from logic.logging_config import configured_logger as logger


class RegionCoords(BaseModel):
    """Pydantic model for region coordinates with validation."""

    x: float = Field(..., ge=0, le=1, description="Normalized x position (0-1)")
    y: float = Field(..., ge=0, le=1, description="Normalized y position (0-1)")
    width: float = Field(..., ge=0, le=1, description="Normalized width (0-1)")
    height: float = Field(..., ge=0, le=1, description="Normalized height (0-1)")

    @validator("x", "y", "width", "height")
    def validate_normalized(cls, v):
        if not 0 <= v <= 1:
            raise ValueError("Coordinates must be normalized between 0 and 1")
        return v

    def to_json(self) -> str:
        """Convert to JSON string for Milvus storage."""
        return json.dumps(self.dict())

    @classmethod
    def from_json(cls, json_str: str) -> "RegionCoords":
        """Create from JSON string."""
        data = json.loads(json_str)
        return cls(**data)


class ElementRelation(BaseModel):
    """Pydantic model for semantic relationships between elements."""

    source_id: str = Field(..., min_length=1, description="Source element ID")
    target_id: str = Field(..., min_length=1, description="Target element ID")
    relation_type: str = Field(
        ..., description="Type of relationship (describes, illustrates, etc.)"
    )
    strength: float = Field(..., ge=0, le=1, description="Confidence score (0-1)")
    direction: str = Field(..., description="Direction of relationship")
    rationale: str = Field(..., max_length=200, description="Brief explanation")
    page_id: str = Field(..., description="Shared page identifier")
    spatial_proximity: Optional[float] = Field(
        None, ge=0, le=1, description="Normalized spatial distance"
    )

    @validator("relation_type")
    def validate_relation_type(cls, v):
        valid_types = [
            "describes",
            "illustrates",
            "supports",
            "contains",
            "references",
            "explains",
            "demonstrates",
            "complements",
            "contrasts",
        ]
        if v not in valid_types:
            raise ValueError(f"Relation type must be one of: {valid_types}")
        return v

    @validator("direction")
    def validate_direction(cls, v):
        valid_directions = [
            "text_to_visual",
            "visual_to_text",
            "element_to_element",
            "bidirectional",
        ]
        if v not in valid_directions:
            raise ValueError(f"Direction must be one of: {valid_directions}")
        return v

    def to_json(self) -> str:
        """Convert to JSON string for storage."""
        return json.dumps(self.dict())

    @classmethod
    def from_json(cls, json_str: str) -> "ElementRelation":
        """Create from JSON string."""
        data = json.loads(json_str)
        return cls(**data)


class MilvusStorage:
    """Enhanced Milvus storage with semantic relationship support and optimized querying."""

    EMBEDDING_DIM = 768  # nomic-embed-text dimensions
    MAX_TEXT_LENGTH = 65535  # Milvus VARCHAR limit
    BATCH_SIZE = 100  # Optimal batch size for inserts

    def __init__(
        self,
        uri: str,
        token: str,
        collection_name: str = "rag_embeddings_enhanced",
        user_name: Optional[str] = None,
        auto_create: bool = True,
        use_mock_on_failure: bool = False,
    ):
        """
        Initialize enhanced Milvus storage with semantic relationship support.

        Args:
            uri: Milvus Cloud URI (required)
            token: Milvus Cloud token (required)
            collection_name: Collection name
            user_name: User name to create user-specific collection
            auto_create: Automatically create collection if not exists
            use_mock_on_failure: Fallback to mock storage if Milvus connection fails
        """
        self.uri = uri
        self.token = token
        # If user_name is provided, use it to create a user-specific collection name
        self.collection_name = f"{user_name}_collection" if user_name else collection_name
        self.auto_create = auto_create
        self.use_mock_on_failure = use_mock_on_failure
        self.client = None
        self.mock_storage = None
        self.is_mock = False
        self._initialize_client()

    def _initialize_client(self):
        """Initialize Milvus client connection."""
        try:
            self.client = MilvusClient(uri=self.uri, token=self.token)
            logger.info(f"Milvus client connected to {self.uri}")

            # Create collection if not exists
            if self.auto_create:
                self._create_collection()
        except Exception as e:
            logger.error(f"Failed to initialize Milvus client: {e}")
            raise FileProcessingError(f"Milvus initialization failed: {e}")

    def _create_collection(self):
        """Create Milvus collection with optimized schema."""
        try:
            # Check if collection exists
            if self.client.has_collection(self.collection_name):
                logger.info(f"Collection {self.collection_name} already exists")

                # Always ensure indexes exist before loading
                self._create_indexes()

                try:
                    # Now try to load collection
                    self.client.load_collection(self.collection_name)
                    # After loading, we can check if collection has data by doing a count
                    try:
                        stats = self.client.query(
                            collection_name=self.collection_name,
                            filter="id != ''",
                            output_fields=["id"],
                            limit=1,
                        )
                        if stats:
                            logger.info(f"Collection {self.collection_name} has data")
                        else:
                            logger.info(f"Collection {self.collection_name} is empty")
                    except Exception:
                        # If query fails, it might be because collection is empty
                        logger.info(
                            f"Collection {self.collection_name} is empty or not ready for queries"
                        )
                    return
                except Exception as load_error:
                    logger.error(
                        f"Failed to load collection even after index creation: {load_error}"
                    )
                    raise FileProcessingError(f"Collection load failed: {load_error}")
            else:
                logger.info(f"Creating collection {self.collection_name}")

            # Define schema for RAG content
            schema = CollectionSchema(
                fields=[
                    FieldSchema(
                        name="id",
                        dtype=DataType.VARCHAR,
                        is_primary=True,
                        max_length=100,
                    ),
                    FieldSchema(
                        name="embedding",
                        dtype=DataType.FLOAT_VECTOR,
                        dim=self.EMBEDDING_DIM,
                    ),
                    FieldSchema(
                        name="text_content",
                        dtype=DataType.VARCHAR,
                        max_length=self.MAX_TEXT_LENGTH,
                    ),
                    FieldSchema(
                        name="content_type",
                        dtype=DataType.VARCHAR,
                        max_length=50,
                        nullable=True,
                        default_value="",
                    ),
                    FieldSchema(
                        name="source_file", dtype=DataType.VARCHAR, max_length=200
                    ),
                    FieldSchema(name="page_id", dtype=DataType.VARCHAR, max_length=50),
                    FieldSchema(name="metadata", dtype=DataType.JSON, max_length=65535),
                    FieldSchema(
                        name="processing_timestamp",
                        dtype=DataType.VARCHAR,
                        max_length=50,
                    ),
                ],
                description="RAG content with multimodal embeddings",
            )

            self.client.create_collection(
                collection_name=self.collection_name, schema=schema
            )

            self._create_indexes()

            # Load the newly created collection
            collection = self.client.load_collection(self.collection_name)
            logger.info(
                f"Collection {self.collection_name} created and loaded successfully"
            )

        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            raise FileProcessingError(f"Collection creation failed: {e}")

    def _create_indexes(self):
        """Create vector index for the collection."""
        try:
            # Check if index already exists by trying to describe it
            try:
                indexes = self.client.describe_index(self.collection_name, "embedding")
                if indexes:
                    logger.info(f"Index already exists for {self.collection_name}")
                    return
            except Exception:
                # If describe_index fails, it might mean no index exists, so we'll try to create one
                pass

            # High recall HNSW index parameters
            index_params = self.client.prepare_index_params("embedding")
            index_params.add_index(
                field_name="embedding",
                index_type="HNSW",
                metric_type="COSINE",
                params={"M": 32, "efConstruction": 400},
            )

            # Create index without loading collection first
            self.client.create_index(
                collection_name=self.collection_name, index_params=index_params
            )
            logger.info(
                f"High recall vector index created for collection {self.collection_name}"
            )
        except Exception as e:
            # Check if the error is about index already existing
            error_msg = str(e).lower()
            if (
                "at most one distinct index is allowed per field" in error_msg
                or "index already exists" in error_msg
                or "index built" in error_msg
            ):
                logger.info(f"Index already exists for {self.collection_name}")
                return
            else:
                raise FileProcessingError(f"Failed to create required index: {e}")

    def insert_single(
        self,
        embedding: List[float],
        text_content: str,
        content_type: str,
        source_file: str,
        page_id: str,
        metadata: Optional[Dict] = None,
        processing_timestamp: Optional[str] = None,
    ) -> str:
        """Insert a single embedding with metadata."""
        try:
            doc_id = str(uuid.uuid4())

            # Prepare metadata
            metadata_dict = metadata or {}
            if processing_timestamp:
                metadata_dict["processing_timestamp"] = processing_timestamp
            else:
                metadata_dict["processing_timestamp"] = time.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

            entities = [
                {
                    "id": doc_id,
                    "embedding": embedding,
                    "text_content": text_content[: self.MAX_TEXT_LENGTH],
                    "content_type": content_type,
                    "source_file": source_file,
                    "page_id": page_id,
                    "metadata": json.dumps(metadata_dict),
                    "processing_timestamp": metadata_dict["processing_timestamp"],
                }
            ]

            # Insert data
            self.client.insert(collection_name=self.collection_name, data=entities)

            logger.debug(
                f"Inserted document {doc_id} into collection {self.collection_name}"
            )
            return doc_id

        except Exception as e:
            logger.error(f"Failed to insert single document: {e}")
            raise FileProcessingError(f"Single insert failed: {e}")

    def insert_batch(self, embeddings_data: List[Dict]) -> List[str]:
        """Insert multiple embeddings with metadata in batch."""
        try:
            if not embeddings_data:
                return []

            doc_ids = []

            # Process in batches
            for i in range(0, len(embeddings_data), self.BATCH_SIZE):
                batch = embeddings_data[i : i + self.BATCH_SIZE]
                entities = []

                for item in batch:
                    doc_id = str(uuid.uuid4())
                    doc_ids.append(doc_id)

                    metadata_dict = item.get("metadata", {})
                    if item.get("processing_timestamp"):
                        metadata_dict["processing_timestamp"] = item[
                            "processing_timestamp"
                        ]
                    else:
                        metadata_dict["processing_timestamp"] = time.strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )

                    entity = {
                        "id": doc_id,
                        "embedding": item["embedding"],
                        "text_content": item["text_content"][: self.MAX_TEXT_LENGTH],
                        # "content_type": item["content_type"],
                        "source_file": item["source_file"],
                        "page_id": item["page_id"],
                        "metadata": json.dumps(metadata_dict),
                        "processing_timestamp": metadata_dict["processing_timestamp"],
                    }
                    entities.append(entity)

                # Insert batch data
                if entities:
                    self.client.insert(
                        collection_name=self.collection_name, data=entities
                    )
                    logger.debug(f"Inserted batch of {len(entities)} documents")

            logger.info(
                f"Successfully inserted {len(doc_ids)} documents into {self.collection_name}"
            )
            return doc_ids

        except Exception as e:
            logger.error(f"Failed to insert batch: {e}")
            raise FileProcessingError(f"Batch insert failed: {e}")

    def search_similar_content(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        content_types: Optional[List[str]] = None,
        source_filter: Optional[str] = None,
    ) -> List[Dict]:
        """Search for similar content using vector similarity."""
        try:
            # Prepare search parameters
            search_params = {"metric_type": "COSINE", "params": {"ef": 10}}

            # Build expression for filtering
            expr = None
            if content_types:
                content_expr = " OR ".join(
                    [f"content_type == '{ct}'" for ct in content_types]
                )
                expr = content_expr
            if source_filter:
                source_expr = f"source_file == '{source_filter}'"
                expr = f"({expr}) if {expr} else {source_expr}" if expr else source_expr

            # Search
            results = self.client.search(
                collection_name=self.collection_name,
                data=[query_embedding],
                anns_field="embedding",
                search_params=search_params,
                limit=top_k,
                filter=expr,
                output_fields=[
                    "id",
                    "text_content",
                    "content_type",
                    "source_file",
                    "page_id",
                    "metadata",
                    "processing_timestamp",
                ],
            )

            # Format results
            formatted_results = []
            for result in results[0]:
                doc = {
                    "id": result.entity.get("id"),
                    "text_content": result.entity.get("text_content", ""),
                    "content_type": result.entity.get("content_type", ""),
                    "source_file": result.entity.get("source_file", ""),
                    "page_id": result.entity.get("page_id", ""),
                    "metadata": result.entity.get("metadata", {}),
                    "processing_timestamp": result.entity.get(
                        "processing_timestamp", ""
                    ),
                    "similarity_score": result.distance,
                }
                formatted_results.append(doc)

            logger.debug(f"Found {len(formatted_results)} similar documents")
            return formatted_results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise FileProcessingError(f"Search failed: {e}")

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        try:
            if self.client.has_collection(self.collection_name):
                collection = self.client.load_collection(self.collection_name)
                stats = collection.query(expr="id != ''", output_fields=["id"], limit=0)
                return {
                    "collection_name": self.collection_name,
                    "total_documents": len(stats) if stats else 0,
                    "embedding_dimension": self.EMBEDDING_DIM,
                    "status": "active",
                }
            else:
                return {
                    "collection_name": self.collection_name,
                    "total_documents": 0,
                    "embedding_dimension": self.EMBEDDING_DIM,
                    "status": "not_exists",
                }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {"error": str(e)}

    def clear_collection(self):
        """Clear all documents from the collection."""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                filter="id != ''",  # Delete all documents
            )
            logger.info(f"Cleared collection {self.collection_name}")
        except Exception as e:
            logger.error(f"Failed to clear collection: {e}")
            raise FileProcessingError(f"Clear failed: {e}")


class MockMilvusStorage:
    """Mock in-memory storage for testing RAG pipeline without Milvus dependency."""

    def __init__(self, collection_name: str = "rag_embeddings_mock"):
        self.collection_name = collection_name
        self.documents = []
        self.embedding_dim = 768
        logger.info(f"Mock storage initialized for collection {collection_name}")

    def insert_single(
        self,
        embedding: List[float],
        text_content: str,
        content_type: str,
        source_file: str,
        page_id: str,
        metadata: Optional[Dict] = None,
        processing_timestamp: Optional[str] = None,
    ) -> str:
        """Insert a single embedding with metadata (mock implementation)."""
        doc_id = str(uuid.uuid4())

        # Prepare metadata
        metadata_dict = metadata or {}
        if processing_timestamp:
            metadata_dict["processing_timestamp"] = processing_timestamp
        else:
            metadata_dict["processing_timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")

        doc = {
            "id": doc_id,
            "embedding": embedding,
            "text_content": text_content[:65535],
            "content_type": content_type,
            "source_file": source_file,
            "page_id": page_id,
            "metadata": metadata_dict,
            "similarity_scores": {},
        }

        self.documents.append(doc)
        logger.debug(f"Mock inserted document {doc_id}")
        return doc_id

    def insert_batch(self, embeddings_data: List[Dict]) -> List[str]:
        """Insert multiple embeddings with metadata in batch (mock implementation)."""
        doc_ids = []

        for item in embeddings_data:
            doc_id = str(uuid.uuid4())
            doc_ids.append(doc_id)

            metadata_dict = item.get("metadata", {})
            if item.get("processing_timestamp"):
                metadata_dict["processing_timestamp"] = item["processing_timestamp"]
            else:
                metadata_dict["processing_timestamp"] = time.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

            doc = {
                "id": doc_id,
                "embedding": item["embedding"],
                "text_content": item["text_content"][:65535],
                "content_type": item["content_type"],
                "source_file": item["source_file"],
                "page_id": item["page_id"],
                "metadata": metadata_dict,
                "similarity_scores": {},
            }
            self.documents.append(doc)

        logger.info(f"Mock inserted {len(doc_ids)} documents")
        return doc_ids

    def search_similar_content(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        content_types: Optional[List[str]] = None,
        source_filter: Optional[str] = None,
    ) -> List[Dict]:
        """Search for similar content using cosine similarity (mock implementation)."""
        if not self.documents:
            return []

        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np

        # Filter documents if needed
        filtered_docs = self.documents
        if content_types:
            filtered_docs = [
                doc for doc in filtered_docs if doc["content_type"] in content_types
            ]
        if source_filter:
            filtered_docs = [
                doc for doc in filtered_docs if doc["source_file"] == source_filter
            ]

        if not filtered_docs:
            return []

        # Convert to numpy arrays for similarity calculation
        doc_embeddings = np.array([doc["embedding"] for doc in filtered_docs])
        query_array = np.array([query_embedding])

        # Calculate cosine similarities
        similarities = cosine_similarity(query_array, doc_embeddings)[0]

        # Get indices sorted by similarity
        similar_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in similar_indices:
            doc = filtered_docs[idx].copy()
            doc["similarity_score"] = float(similarities[idx])
            results.append(doc)

        logger.debug(f"Mock search returned {len(results)} similar documents")
        return results

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics (mock implementation)."""
        return {
            "collection_name": self.collection_name,
            "total_documents": len(self.documents),
            "embedding_dimension": self.embedding_dim,
            "status": "loaded",
        }

    def clear_collection(self):
        """Clear all documents from the collection (mock implementation)."""
        self.documents.clear()
        logger.info(f"Mock collection {self.collection_name} cleared")
