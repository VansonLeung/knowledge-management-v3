# Knowledge Management V3

A small local-first stack for ingesting documents, chunking them, generating embeddings/metadata via an OpenAI-compatible API, and indexing into Elasticsearch for retrieval (with planned Neo4j enrichment for hybrid search).

## Components
- **pymupdf_service (port 17002):** Converts PDFs to markdown and extracts per-page text/metadata.
- **mineru_service (port 16007):** High-accuracy PDF/image → markdown/JSON using MinerU with MLX acceleration on Apple Silicon.
- **chunking_service (port 17006):** Multilingual-aware text chunker with overlap control.
- **openai_embedding_client_service (port 16003):** Proxies `/embeddings` to `OPENAI_API_BASE` (defaults to http://localhost:18000/v1, model `moka-ai/m3e-base`).
- **openai_llm_client_service (port 17004):** Proxies chat/metadata/RAG requests to `OPENAI_API_BASE` (default model `Qwen3-4B-Instruct-2507-4bit`, supports SSE streaming).
- **ES controller (mainservices/es_controller):** Thin helpers around Elasticsearch for indexes/docs.
- **Workflows (mainservices/workflows):** CLI scripts to ingest PDFs, browse/clean indexes, and run vector + RAG search.

## Prerequisites
- Python 3.10+
- Running services: Elasticsearch on `http://localhost:9200` (no security) or adjust creds; optional Docker compose in `microservices/docker-compose-elastic-search`.
- OpenAI-compatible endpoint at `http://localhost:18000/v1` (override with env `OPENAI_API_BASE`).

## Install deps
From repo root:
```bash
venv/bin/pip install -r microservices/pymupdf_service/requirements.txt
venv/bin/pip install -r microservices/mineru_service/requirements.txt   # MinerU with MLX (macOS)
venv/bin/pip install -r microservices/chunking_service/requirements.txt
venv/bin/pip install -r microservices/markdown_analysis_service/requirements.txt
venv/bin/pip install -r microservices/openai_embedding_client_service/requirements.txt
venv/bin/pip install -r microservices/openai_llm_client_service/requirements.txt
venv/bin/pip install -r mainservices/es_controller/requirements.txt
```

## Run services (local dev)
```bash
venv/bin/python3 microservices/pymupdf_service/main.py
venv/bin/python3 microservices/mineru_service/main.py
venv/bin/python3 microservices/chunking_service/main.py
venv/bin/python3 microservices/markdown_analysis_service/main.py
venv/bin/python3 microservices/openai_embedding_client_service/main.py
venv/bin/python3 microservices/openai_llm_client_service/main.py
# ensure Elasticsearch is running at http://localhost:9200 (elastic/octopuspass if secured)
```

Or launch/stop all five apps with a single helper script (logs are prefixed per service and everything terminates together):

```bash
venv/bin/python3 scripts/run_services.py
# optional: KM_PYTHON=/custom/python python3 scripts/run_services.py
```

### MinerU service configuration
The MinerU service (`mineru_service`) supports these environment variables:
| Variable | Default | Description |
|----------|---------|-------------|
| `MINERU_BACKEND` | `vlm-mlx-engine` | Inference backend (`vlm-mlx-engine`, `vlm-transformers`, `pipeline`) |
| `MINERU_CONCURRENCY` | `1` | Max parallel requests; `0` = unlimited, `1` = serial (lower RAM) |
| `MINERU_CACHE_DIR` | `~/.cache/mineru` | Model weights cache directory |

On first request the service downloads ~10–20 GB of model weights to `MINERU_CACHE_DIR`. Subsequent runs reuse the cache.

## Dockerized stack
1. Build and start everything (pymupdf, chunking, embedding proxy, LLM proxy, and Elasticsearch) with Docker Compose:
  ```bash
  docker compose up --build
  ```
  Add `-d` to run in the background. Stop everything with `docker compose down` (include `-v` to drop the Elasticsearch volume).
2. Configure upstream LLM/embedding access via environment variables (either an `.env` file or inline when invoking Compose):
  - `OPENAI_API_BASE` (default `http://host.docker.internal:18000/v1` so the containers can reach a host-local API)
  - `OPENAI_API_KEY` (optional, forwarded to both proxy services)
  - `OPENAI_EMBED_MODEL`, `OPENAI_LLM_MODEL`, `OPENAI_TIMEOUT`
3. The containers expose the same ports described above (`17002`, `16003`, `17004`, `17006`, `9200`), so local workflows keep working without code changes.

> **Note:** On Linux you may need to replace `host.docker.internal` with the host IP address or add it manually (e.g., `--add-host=host.docker.internal:host-gateway`).

### Running CLI workflows against Docker services
You can continue to execute the ingestion/search workflows from your host Python environment; they will call into the containerized services the same way as the locally started processes. Ensure your virtualenv has the `mainservices/es_controller` requirements installed, then run the commands from the "Workflows" section.

## Workflows
- **Ingest PDF to ES:**  
  `venv/bin/python3 -m mainservices.workflows.ingest_workflow --pdf "references/Functions_and_Features_-_Overall_summary_V4 (1).pdf" --index a-001`
- **Browse docs:**  
  `venv/bin/python3 -m mainservices.workflows.browse_docs_by_index --index a-001 --limit 10`
- **Clean docs / drop index:**  
  `venv/bin/python3 -m mainservices.workflows.clean_docs_by_index --index a-001`  
  `venv/bin/python3 -m mainservices.workflows.clean_docs_and_indexes --index a-001`
- **Vector + RAG search:**  
  `venv/bin/python3 -m mainservices.workflows.es_search_by_index --index a-001 --rag --rag-stream`
- **LLM ping test:**  
  `venv/bin/python3 -m mainservices.workflows.es_search_by_index --llm-test`

## Hybrid search intent
The ES controller and planned Neo4j workflows aim to combine:
- **Elasticsearch:** fast text/vector search over chunked content.
- **Neo4j:** relationship/graph layer for entity links and advanced traversal.

As Neo4j pieces are added, this README will be updated with graph workflows and combined retrieval examples.
