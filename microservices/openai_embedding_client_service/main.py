import os
from typing import List, Optional, Union

import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

DEFAULT_MODEL = os.getenv("OPENAI_EMBED_MODEL", "moka-ai/m3e-base")
API_BASE = os.getenv("OPENAI_API_BASE", "http://localhost:18000/v1")
API_KEY = os.getenv("OPENAI_API_KEY")
REQUEST_TIMEOUT = int(os.getenv("OPENAI_TIMEOUT", "60"))

app = FastAPI(title="OpenAI Embedding Client Service")


class EmbeddingRequest(BaseModel):
    input: Union[str, List[str]] = Field(..., description="Text or list of texts to embed")
    model: Optional[str] = Field(None, description="Override embedding model")


class EmbeddingResponse(BaseModel):
    model: str
    embeddings: List[List[float]]
    usage: Optional[dict] = None


def _headers() -> dict:
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    return headers


def _normalize_inputs(data: Union[str, List[str]]) -> List[str]:
    if isinstance(data, str):
        return [data]
    return list(data)


def _extract_embeddings(payload: dict) -> List[List[float]]:
    records = payload.get("data") or []
    embeddings: List[List[float]] = []
    for item in records:
        if "embedding" in item:
            embeddings.append(item["embedding"])
    return embeddings


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/embed", response_model=EmbeddingResponse)
async def create_embeddings(request: EmbeddingRequest):
    inputs = _normalize_inputs(request.input)
    model = request.model or DEFAULT_MODEL
    payload = {"input": inputs, "model": model}

    try:
        resp = requests.post(
            f"{API_BASE}/embeddings",
            headers=_headers(),
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        body = resp.json()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Embedding request failed: {exc}")
    except ValueError:
        raise HTTPException(status_code=500, detail="Invalid response from embedding provider")

    embeddings = _extract_embeddings(body)
    if not embeddings:
        raise HTTPException(status_code=500, detail="No embeddings returned from provider")

    return EmbeddingResponse(model=model, embeddings=embeddings, usage=body.get("usage"))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=16003)
