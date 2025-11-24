from typing import Any, Dict, Optional

from mainservices.es_controller.es_client.EsClient import EsClient, get_default_client


def update_document(
    index_name: str,
    doc_id: str,
    document: Dict[str, Any],
    client: Optional[EsClient] = None,
):
    es = client or get_default_client()
    return es.update_document(index=index_name, doc_id=doc_id, document=document)


def upsert_metadata_field(
    index_name: str,
    doc_id: str,
    field_name: str,
    value: Any,
    metadata_field: str = "document_chunk_tags",
    client: Optional[EsClient] = None,
):
    """
    Upsert a single metadata field on a document (defaults to document_chunk_tags).
    Creates the metadata container if it does not exist and adds/overwrites the field.
    """
    es = client or get_default_client()
    script = {
        "source": """
            if (ctx._source[params.metaField] == null) {
                ctx._source[params.metaField] = [:];
            }
            ctx._source[params.metaField][params.field] = params.value;
        """,
        "params": {"metaField": metadata_field, "field": field_name, "value": value},
    }
    upsert_doc = {metadata_field: {field_name: value}}
    return es.client.update(index=index_name, id=doc_id, script=script, upsert=upsert_doc)
