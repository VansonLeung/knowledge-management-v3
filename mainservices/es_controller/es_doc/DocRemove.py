from typing import Optional

from mainservices.es_controller.es_client.EsClient import EsClient, get_default_client


def delete_document(index_name: str, doc_id: str, client: Optional[EsClient] = None):
    es = client or get_default_client()
    return es.delete_document(index=index_name, doc_id=doc_id)
