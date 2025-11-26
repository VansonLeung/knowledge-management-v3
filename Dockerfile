# syntax=docker/dockerfile:1.6
ARG PYTHON_VERSION=3.11

FROM python:${PYTHON_VERSION}-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libglib2.0-0 \
        libgl1 \
        libxrender1 \
        libxext6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

FROM base AS pymupdf_service
COPY microservices/pymupdf_service/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY microservices/pymupdf_service/ /app
EXPOSE 16002
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "16002"]

FROM base AS chunking_service
COPY microservices/chunking_service/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY microservices/chunking_service/ /app
EXPOSE 16006
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "16006"]

FROM base AS openai_embedding_client_service
COPY microservices/openai_embedding_client_service/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY microservices/openai_embedding_client_service/ /app
EXPOSE 16003
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "16003"]

FROM base AS openai_llm_client_service
COPY microservices/openai_llm_client_service/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY microservices/openai_llm_client_service/ /app
EXPOSE 16004
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "16004"]
