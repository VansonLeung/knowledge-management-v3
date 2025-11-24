import argparse

from mainservices.es_controller.es_client.EsClient import get_default_client


def clean_docs(index_name: str):
    client = get_default_client()
    if not client.index_exists(index_name):
        print(f"Index '{index_name}' does not exist; nothing to delete.")
        return
    res = client.client.delete_by_query(
        index=index_name,
        body={"query": {"match_all": {}}},
        conflicts="proceed",
        refresh=True,
    )
    print(f"Deleted docs from '{index_name}': {res}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Remove all documents from an index.")
    parser.add_argument("--index", default="a-001", help="Elasticsearch index name (default: a-001)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    clean_docs(args.index)
