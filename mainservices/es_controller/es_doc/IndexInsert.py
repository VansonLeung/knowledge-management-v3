from typing import Any, Dict, Optional

from mainservices.es_controller.es_client.EsClient import EsClient, get_default_client

DEFAULT_VECTOR_DIM = 768


def default_mappings(vector_dim: int = DEFAULT_VECTOR_DIM) -> Dict[str, Any]:
    return {
        "properties": {
            "text": {"type": "text"},
            "vector": {
                "type": "dense_vector",
                "dims": vector_dim,
                "index": True,
                "similarity": "cosine",
            },
            "document_file_id": {"type": "keyword"},
            "document_file_name": {"type": "keyword"},
            "document_file_size": {"type": "long"},
            "document_chunk_tags": {"type": "object", "enabled": True},
            "pages_total": {"type": "integer"},
            "page_number": {"type": "integer"},
        }
    }


def create_index(
    index_name: str,
    client: Optional[EsClient] = None,
    mappings: Optional[Dict[str, Any]] = None,
    settings: Optional[Dict[str, Any]] = None,
    vector_dim: int = DEFAULT_VECTOR_DIM,
) -> Dict[str, Any]:
    es = client or get_default_client()
    resolved_mappings = mappings or default_mappings(vector_dim=vector_dim)
    return es.create_index(index=index_name, mappings=resolved_mappings, settings=settings)
