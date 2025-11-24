from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional

from elasticsearch import Elasticsearch, helpers


@dataclass
class EsClientConfig:
    host: str = "http://localhost:9200"
    username: str = "elastic"
    password: str = "octopuspass"
    verify_certs: bool = False
    request_timeout: int = 30


class EsClient:
    def __init__(self, config: Optional[EsClientConfig] = None):
        self.config = config or EsClientConfig()
        self.client = Elasticsearch(
            self.config.host,
            basic_auth=(self.config.username, self.config.password),
            verify_certs=self.config.verify_certs,
            request_timeout=self.config.request_timeout,
        )

    def ping(self) -> bool:
        return bool(self.client.ping())

    def index_exists(self, index: str) -> bool:
        return self.client.indices.exists(index=index)

    def create_index(self, index: str, mappings: Optional[Dict[str, Any]] = None, settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if self.index_exists(index):
            return {"acknowledged": True, "index": index, "message": "already_exists"}
        body: Dict[str, Any] = {}
        if settings:
            body["settings"] = settings
        if mappings:
            body["mappings"] = mappings
        return self.client.indices.create(index=index, **body)

    def delete_index(self, index: str) -> Dict[str, Any]:
        if not self.index_exists(index):
            return {"acknowledged": True, "index": index, "message": "not_found"}
        return self.client.indices.delete(index=index)

    def put_mapping(self, index: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        return self.client.indices.put_mapping(index=index, properties=properties)

    def index_document(self, index: str, document: Dict[str, Any], doc_id: Optional[str] = None, refresh: bool = False) -> Dict[str, Any]:
        return self.client.index(index=index, id=doc_id, document=document, refresh=refresh)

    def update_document(self, index: str, doc_id: str, document: Dict[str, Any]) -> Dict[str, Any]:
        return self.client.update(index=index, id=doc_id, doc=document)

    def delete_document(self, index: str, doc_id: str) -> Dict[str, Any]:
        return self.client.delete(index=index, id=doc_id)

    def bulk_index(self, index: str, documents: Iterable[Dict[str, Any]], refresh: bool = False) -> Dict[str, Any]:
        actions = (
            {"_index": index, "_id": doc.get("_id"), "_source": doc}
            for doc in documents
        )
        success, errors = helpers.bulk(self.client, actions, refresh=refresh, stats_only=False)
        return {"success": success, "errors": errors}


def get_default_client() -> EsClient:
    return EsClient()
