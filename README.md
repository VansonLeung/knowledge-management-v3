# Knowledge Management V3

A small local-first stack for ingesting documents, chunking them, generating embeddings/metadata via an OpenAI-compatible API, and indexing into Elasticsearch for retrieval (with planned Neo4j enrichment for hybrid search).

## Components
- **pymupdf_service (port 16002):** Converts PDFs to markdown and extracts per-page text/metadata.
- **chunking_service (port 16006):** Multilingual-aware text chunker with overlap control.
- **openai_embedding_client_service (port 16003):** Proxies `/embeddings` to `OPENAI_API_BASE` (defaults to http://localhost:18000/v1, model `moka-ai/m3e-base`).
- **openai_llm_client_service (port 16004):** Proxies chat/metadata/RAG requests to `OPENAI_API_BASE` (default model `Qwen3-4B-Instruct-2507-4bit`, supports SSE streaming).
- **ES controller (mainservices/es_controller):** Thin helpers around Elasticsearch for indexes/docs.
- **Workflows (mainservices/workflows):** CLI scripts to ingest PDFs, browse/clean indexes, and run vector + RAG search.

## Prerequisites
- Python 3.10+
- Running services: Elasticsearch on `http://localhost:9200` (no security) or adjust creds; optional Docker compose in `microservices/docker-compose-elastic-search`.
- OpenAI-compatible endpoint at `http://localhost:18000/v1` (override with env `OPENAI_API_BASE`).

## Install deps
From repo root:
```bash
pip install -r microservices/pymupdf_service/requirements.txt
pip install -r microservices/chunking_service/requirements.txt
pip install -r microservices/openai_embedding_client_service/requirements.txt
pip install -r microservices/openai_llm_client_service/requirements.txt
pip install -r mainservices/es_controller/requirements.txt
```

## Run services (local dev)
```bash
python microservices/pymupdf_service/main.py
python microservices/chunking_service/main.py
python microservices/openai_embedding_client_service/main.py
python microservices/openai_llm_client_service/main.py
# ensure Elasticsearch is running at http://localhost:9200 (elastic/octopuspass if secured)
```

## Workflows
- **Ingest PDF to ES:**  
  `python -m mainservices.workflows.ingest_workflow.py --pdf references/Functions_and_Features_-_Overall_summary_V4\ (1).pdf --index a-001`
- **Browse docs:**  
  `python -m mainservices.workflows.browse_docs_by_index.py --index a-001 --limit 10`
- **Clean docs / drop index:**  
  `python -m mainservices.workflows.clean_docs_by_index.py --index a-001`  
  `python -m mainservices.workflows.clean_docs_and_indexes.py --index a-001`
- **Vector + RAG search:**  
  `python -m mainservices.workflows.es_search_by_index.py --index a-001 --rag --rag-stream`
- **LLM ping test:**  
  `python -m mainservices.workflows.es_search_by_index.py --llm-test`

## Hybrid search intent
The ES controller and planned Neo4j workflows aim to combine:
- **Elasticsearch:** fast text/vector search over chunked content.
- **Neo4j:** relationship/graph layer for entity links and advanced traversal.

As Neo4j pieces are added, this README will be updated with graph workflows and combined retrieval examples.
