import argparse

from mainservices.es_controller.es_doc.IndexRemove import delete_index


def clean(index_name: str):
    result = delete_index(index_name)
    print(f"Deleted index '{index_name}': {result}")


def parse_args():
    parser = argparse.ArgumentParser(description="Delete an Elasticsearch index and all docs within it.")
    parser.add_argument("--index", default="a-001", help="Index name to delete (default: a-001)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    clean(args.index)
