import argparse
from collections import defaultdict
from typing import Dict, Iterable, List, Optional

import requests

from mainservices.es_controller.es_client.EsClient import get_default_client


class EmbeddingServiceClient:
    def __init__(self, base_url: str = "http://localhost:16003"):
        self.base_url = base_url.rstrip("/")

    def embed(self, text: str) -> List[float]:
        url = f"{self.base_url}/embed"
        payload = {"input": text}
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        body = response.json()
        embeddings = body.get("embeddings") or []
        if not embeddings:
            raise RuntimeError("Embedding service returned no vectors")
        return embeddings[0]


class LLMServiceClient:
    def __init__(self, base_url: str = "http://localhost:16004"):
        self.base_url = base_url.rstrip("/")

    def chat(self, prompt: str) -> str:
        url = f"{self.base_url}/chat"
        payload = {"prompt": prompt}
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        return response.json().get("content", "")

    def answer_with_contexts(self, question: str, contexts: List[Dict]) -> str:
        url = f"{self.base_url}/rag"
        payload = {"question": question, "contexts": contexts}
        response = requests.post(url, json=payload, timeout=90)
        response.raise_for_status()
        body = response.json()
        return body.get("answer", "")

    def stream_answer_with_contexts(self, question: str, contexts: List[Dict]) -> Iterable[str]:
        url = f"{self.base_url}/rag/stream"
        payload = {"question": question, "contexts": contexts}
        with requests.post(url, json=payload, stream=True, timeout=120) as response:
            response.raise_for_status()
            for raw in response.iter_lines():
                if raw is None:
                    continue
                if raw.startswith(b"data:"):
                    raw = raw[5:]
                    if raw.startswith(b" "):
                        raw = raw[1:]
                if raw == b"[DONE]":
                    break
                if raw.startswith(b"[ERROR]"):
                    raise RuntimeError(raw.decode("utf-8", errors="replace"))
                if not raw:
                    continue
                yield raw.decode("utf-8", errors="replace")


def vector_search(index_name: str, query_vector: List[float], k: int = 10, num_candidates: int = 30):
    client = get_default_client()
    if not client.index_exists(index_name):
        raise RuntimeError(f"Index '{index_name}' does not exist")

    res = client.client.search(
        index=index_name,
        knn={
            "field": "vector",
            "query_vector": query_vector,
            "k": k,
            "num_candidates": num_candidates,
        },
        _source=True,
    )
    hits = res.get("hits", {}).get("hits", [])
    # Attach score to source for simpler downstream printing
    for hit in hits:
        score = hit.get("_score")
        if "_source" in hit:
            hit["_source"]["__score"] = score
    return hits


def group_by_document(hits: List[Dict]) -> Dict[str, List[Dict]]:
    grouped = defaultdict(list)
    for hit in hits:
        source = hit.get("_source", {})
        doc_id = source.get("document_file_id", "unknown")
        grouped[doc_id].append(source)
    for doc_id, docs in grouped.items():
        docs.sort(key=lambda d: d.get("chunk_index", 0))
    return grouped


def build_contexts(hits: List[Dict], limit: int = 6) -> List[Dict]:
    contexts = []
    for hit in hits[:limit]:
        source = hit.get("_source", {}) or {}
        text = source.get("text")
        if not text:
            continue
        contexts.append(
            {
                "text": text,
                "score": source.get("__score"),
                "metadata": {
                    "page_number": source.get("page_number"),
                    "chunk_index": source.get("chunk_index"),
                    "document_file_name": source.get("document_file_name"),
                    "document_file_id": source.get("document_file_id"),
                },
            }
        )
    return contexts


def run_search(
    questions: List[str],
    index_name: str,
    embedding_url: str,
    rag: bool = False,
    llm_url: Optional[str] = None,
    stream: bool = False,
):
    embedder = EmbeddingServiceClient(embedding_url)
    llm = LLMServiceClient(llm_url) if rag else None
    for question in questions:
        print(f"\n=== Question: {question}")
        try:
            vector = embedder.embed(question)
            hits = vector_search(index_name, vector)
        except Exception as exc:
            print(f"Search failed: {exc}")
            continue

        grouped = group_by_document(hits)
        if not grouped:
            print("No results.")
            continue

        for doc_id, chunks in grouped.items():
            print(f"\nDocument: {doc_id} ({chunks[0].get('document_file_name')})")
            for chunk in chunks:
                score = chunk.get("__score") or ""
                print(f"  page={chunk.get('page_number')} chunk={chunk.get('chunk_index')} score={score}")
                text_snippet = (chunk.get("text") or "")[:200].replace("\n", " ")
                print(f"    {text_snippet}...")

        if rag and llm:
            contexts = build_contexts(hits)
            if contexts:
                try:
                    print("\n-- LLM Answer --")
                    if stream:
                        for token in llm.stream_answer_with_contexts(question, contexts):
                            print(token, end="", flush=True)
                        print()  # newline after stream
                    else:
                        answer = llm.answer_with_contexts(question, contexts)
                        print(answer)
                except Exception as exc:
                    print(f"LLM answer failed: {exc}")
            else:
                print("No contexts available for LLM answer.")


def parse_args():
    parser = argparse.ArgumentParser(description="Search an index using question embeddings.")
    parser.add_argument("--index", default="a-001", help="Index name (default: a-001)")
    parser.add_argument("--embedding-url", default="http://localhost:16003", help="Embedding service URL")
    parser.add_argument("--llm-url", default="http://localhost:16004", help="LLM service URL")
    parser.add_argument("--rag", action="store_true", help="If set, ask LLM to answer using retrieved chunks.")
    parser.add_argument("--rag-stream", action="store_true", help="Stream LLM answer via SSE when using --rag.")
    parser.add_argument("--llm-test", action="store_true", help="Send a test prompt ('hi , how are you?') to the LLM chat endpoint.")
    parser.add_argument(
        "--questions",
        nargs="*",
        help="Questions to search; defaults to a few sample queries.",
    )
    return parser.parse_args()


DEFAULT_QUESTIONS = [
    "What are the main functions and features described?",
    "Who is the target audience?",
    "What events are mentioned?",
    "What is the capital of France?",
    "Is ordering system required?",
    "What programming languages are required?",
    "Is Google Cloud Storage required?",
]


if __name__ == "__main__":
    args = parse_args()
    questions = args.questions or DEFAULT_QUESTIONS
    if args.llm_test:
        tester = LLMServiceClient(args.llm_url)
        try:
            print("LLM test prompt: hi , how are you?")
            reply = tester.chat("hi , how are you?")
            print(f"LLM test reply: {reply}")
        except Exception as exc:
            print(f"LLM test failed: {exc}")
    run_search(
        questions,
        args.index,
        args.embedding_url,
        rag=args.rag,
        llm_url=args.llm_url,
        stream=args.rag_stream,
    )
