import argparse
import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional

import requests

from mainservices.es_controller.es_doc.DocInsert import insert_document
from mainservices.es_controller.es_doc.IndexInsert import create_index, DEFAULT_VECTOR_DIM


class PymupdfServiceClient:
    def __init__(self, base_url: str = "http://localhost:16002"):
        self.base_url = base_url.rstrip("/")

    def analyze_pdf(self, pdf_path: Path) -> Dict:
        url = f"{self.base_url}/analyze/pdf"
        with pdf_path.open("rb") as handle:
            files = {"file": (pdf_path.name, handle, "application/pdf")}
            response = requests.post(url, files=files, timeout=120)
        response.raise_for_status()
        return response.json()


class ChunkingServiceClient:
    def __init__(self, base_url: str = "http://localhost:16006"):
        self.base_url = base_url.rstrip("/")

    def chunk(
        self,
        text: str,
        chunk_size_words: int = 512,
        chunk_overlap_words: int = 50,
        metadata: Optional[Dict] = None,
    ) -> List[Dict]:
        approx_chars = chunk_size_words * 6
        approx_overlap = chunk_overlap_words * 6
        payload = {
            "text": text,
            "chunk_size": approx_chars,
            "chunk_overlap": approx_overlap,
            "metadata": metadata or {},
            "language_hint": "english",
        }
        url = f"{self.base_url}/chunk"
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        body = response.json()
        return body.get("chunks", [])


class EmbeddingServiceClient:
    def __init__(self, base_url: str = "http://localhost:16003"):
        self.base_url = base_url.rstrip("/")

    def embed(self, text: str) -> List[float]:
        url = f"{self.base_url}/embed"
        payload = {"input": text}
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
        body = response.json()
        embeddings = body.get("embeddings") or []
        if not embeddings:
            raise RuntimeError("Embedding service returned no vectors")
        return embeddings[0]


class LLMServiceClient:
    def __init__(self, base_url: str = "http://localhost:17004"):
        self.base_url = base_url.rstrip("/")

    def extract_metadata(self, text: str) -> Dict:
        url = f"{self.base_url}/metadata"
        payload = {"text": text}
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
        body = response.json()
        return body.get("metadata") or {}


class ElasticIndexer:
    def __init__(self, index_name: str = "a-001"):
        self.index_name = index_name

    def ensure_index(self):
        create_index(index_name=self.index_name, vector_dim=DEFAULT_VECTOR_DIM)

    def insert(self, document: Dict, doc_id: Optional[str] = None):
        insert_document(self.index_name, document, doc_id=doc_id, refresh=False)


class IngestionWorkflow:
    def __init__(
        self,
        pdf_path: Path,
        index_name: str = "a-001",
        pymupdf_url: str = "http://localhost:16002",
        chunking_url: str = "http://localhost:16006",
        embedding_url: str = "http://localhost:16003",
        llm_url: str = "http://localhost:17004",
    ):
        self.pdf_path = pdf_path
        self.file_id = str(uuid.uuid4())
        self.indexer = ElasticIndexer(index_name=index_name)
        self.pymupdf = PymupdfServiceClient(pymupdf_url)
        self.chunker = ChunkingServiceClient(chunking_url)
        self.embedding = EmbeddingServiceClient(embedding_url)
        self.llm = LLMServiceClient(llm_url)

    def run(self):
        analysis = self.pymupdf.analyze_pdf(self.pdf_path)
        pages = analysis.get("pages", [])
        pages_total = len(pages)
        self.indexer.ensure_index()

        for page in pages:
            text = page.get("markdown") or page.get("text") or ""
            if not text:
                continue
            page_number = page.get("page") or 0
            metadata_base = {
                "document_file_id": self.file_id,
                "document_file_name": self.pdf_path.name,
                "document_file_size": self.pdf_path.stat().st_size,
                "pages_total": pages_total,
                "page_number": page_number,
            }

            chunks = self.chunker.chunk(
                text,
                chunk_size_words=512,
                chunk_overlap_words=50,
                metadata=metadata_base,
            )
            for chunk in chunks:
                chunk_text = chunk.get("text") or ""
                chunk_meta = {**metadata_base, **(chunk.get("metadata") or {})}
                metadata = self.llm.extract_metadata(chunk_text)
                embedding = self.embedding.embed(chunk_text)
                embedding_text_meta = self.embedding.embed(f"{chunk_text} ( {json.dumps(metadata)} )")
                doc = {
                    "text": chunk_text,
                    "vector": embedding,
                    "vector_text_meta": embedding_text_meta,
                    "document_file_id": chunk_meta["document_file_id"],
                    "document_file_name": chunk_meta["document_file_name"],
                    "document_file_size": chunk_meta["document_file_size"],
                    "document_chunk_tags": metadata,
                    "pages_total": chunk_meta.get("pages_total"),
                    "page_number": chunk_meta.get("page_number"),
                    "chunk_index": chunk_meta.get("chunk_index"),
                }
                doc_id = f"{self.file_id}-{page_number}-{chunk_meta.get('chunk_index', len(chunk_text))}"
                self.indexer.insert(doc, doc_id=doc_id)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest a PDF into Elasticsearch via local microservices.")
    parser.add_argument(
        "--pdf",
        default="references/Functions_and_Features_-_Overall_summary_V4 (1).pdf",
        help="Path to the PDF to ingest.",
    )
    parser.add_argument("--index", default="a-001", help="Elasticsearch index name.")
    parser.add_argument("--pymupdf-url", default="http://localhost:16002", help="PyMuPDF service base URL.")
    parser.add_argument("--chunking-url", default="http://localhost:16006", help="Chunking service base URL.")
    parser.add_argument("--embedding-url", default="http://localhost:16003", help="Embedding service base URL.")
    parser.add_argument("--llm-url", default="http://localhost:17004", help="LLM service base URL.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    workflow = IngestionWorkflow(
        pdf_path=Path(args.pdf),
        index_name=args.index,
        pymupdf_url=args.pymupdf_url,
        chunking_url=args.chunking_url,
        embedding_url=args.embedding_url,
        llm_url=args.llm_url,
    )
    workflow.run()
