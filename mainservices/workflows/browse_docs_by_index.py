import argparse
from typing import Iterable

from elasticsearch import helpers

from mainservices.es_controller.es_client.EsClient import get_default_client


def iter_docs(index_name: str) -> Iterable[dict]:
    client = get_default_client()
    if not client.index_exists(index_name):
        print(f"Index '{index_name}' does not exist.")
        return []
    return helpers.scan(
        client.client,
        index=index_name,
        query={"query": {"match_all": {}}},
        _source=True,
    )


def browse(index_name: str, limit: int):
    count = 0
    for hit in iter_docs(index_name):
        source = hit.get("_source", {})
        doc_id = hit.get("_id")
        print(f"\nID: {doc_id}")
        print(f"page={source.get('page_number')} chunk={source.get('chunk_index')}")
        print(f"file={source.get('document_file_name')} ({source.get('document_file_id')})")
        print(f"tags={source.get('document_chunk_tags')}")
        print(f"text: {source.get('text', '')[:200]}...")
        count += 1
        if count >= limit:
            break
    if count == 0:
        print("No documents found.")
    else:
        print(f"\nDisplayed {count} documents from '{index_name}'.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="List documents from an Elasticsearch index.")
    parser.add_argument("--index", default="a-001", help="Index name (default: a-001)")
    parser.add_argument("--limit", type=int, default=20, help="Max documents to display (default: 20)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    browse(args.index, args.limit)
