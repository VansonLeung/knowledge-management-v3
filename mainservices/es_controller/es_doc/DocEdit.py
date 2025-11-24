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
