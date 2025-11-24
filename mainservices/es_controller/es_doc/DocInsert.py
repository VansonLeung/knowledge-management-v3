from typing import Any, Dict, Optional

from mainservices.es_controller.es_client.EsClient import EsClient, get_default_client


def insert_document(
    index_name: str,
    document: Dict[str, Any],
    doc_id: Optional[str] = None,
    client: Optional[EsClient] = None,
    refresh: bool = False,
) -> Dict[str, Any]:
    es = client or get_default_client()
    return es.index_document(index=index_name, document=document, doc_id=doc_id, refresh=refresh)
