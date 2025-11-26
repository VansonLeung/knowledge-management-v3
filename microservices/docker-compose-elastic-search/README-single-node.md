# Single-node Elasticsearch docker-compose

This compose file provides a single-node Elasticsearch setup suitable for local development and tests.

File: `docker-compose-single.yml`

Key considerations:
- Uses `discovery.type=single-node` to avoid cluster bootstrapping complexities.
- `ES_JAVA_OPTS=-Xms1g -Xmx1g` and `mem_limit` defaults to 2GB (`MEM_LIMIT_SINGLE`). Adjust as needed.
- `restart: unless-stopped` added so the container restarts if transient failures occur.
- Persistent logs: `./logs/elasticsearch` and Kibana logs for easier debugging.
- Useful environment variables in `.env`:
  - `STACK_VERSION` (e.g., 8.11.3)
  - `CLUSTER_NAME`
  - `ELASTIC_PASSWORD`, `KIBANA_PASSWORD` (only for Kibana)
  - `ES_PORT`, `KIBANA_PORT`
   - plugin `analysis-ik-8.11.3` must exist at the repo root; the setup container now **fails immediately** if that folder is missing (no remote download fallback).

Quick run:

```bash
# Start the single-node stack in the background
docker compose -f docker-compose-single.yml up -d

# Follow Elasticsearch logs
docker compose -f docker-compose-single.yml logs -f elasticsearch

# Check cluster health
curl -s http://localhost:9200/_cluster/health?pretty

# If Kibana enabled, check Kibana health and logs
curl -s http://localhost:5601
docker compose -f docker-compose-single.yml logs -f kibana
```

# `docker compose up` automatically runs the `setup` helper and only needs it to finish successfully, but you can run it manually if you want to inspect its output:

```bash
# Run setup in foreground to see output
docker compose -f docker-compose-single.yml up setup

# Then bring up the elasticsearch service
docker compose -f docker-compose-single.yml up -d elasticsearch
```

Host prerequisites:
- On Linux: `sudo sysctl -w vm.max_map_count=262144`
- On macOS (Docker Desktop): ensure the VM has at least 2GB of RAM allocated in Docker Desktop settings.

Troubleshooting:
- If container is OOM-killed, lower `ES_JAVA_OPTS` to `-Xms512m -Xmx512m` or increase `MEM_LIMIT_SINGLE` in the `.env`.
- For persistent problems, enable `xpack.monitoring` and persist logs to analyze GC and node metrics.
