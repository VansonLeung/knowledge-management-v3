from typing import Optional

from mainservices.es_controller.es_client.EsClient import EsClient, get_default_client


def delete_index(index_name: str, client: Optional[EsClient] = None):
    es = client or get_default_client()
    return es.delete_index(index_name)
