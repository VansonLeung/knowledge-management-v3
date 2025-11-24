from typing import Any, Dict, Optional

from mainservices.es_controller.es_client.EsClient import EsClient, get_default_client


def update_mappings(
    index_name: str,
    properties: Dict[str, Any],
    client: Optional[EsClient] = None,
) -> Dict[str, Any]:
    es = client or get_default_client()
    return es.put_mapping(index=index_name, properties=properties)


def update_settings(
    index_name: str,
    settings: Dict[str, Any],
    client: Optional[EsClient] = None,
) -> Dict[str, Any]:
    es = client or get_default_client()
    return es.client.indices.put_settings(index=index_name, settings=settings)
