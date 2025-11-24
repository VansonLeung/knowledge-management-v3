import json
import os
from typing import Any, Dict, List, Optional

import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

DEFAULT_MODEL = os.getenv("OPENAI_LLM_MODEL", "Qwen3-4B-Instruct-2507-4bit")
API_BASE = os.getenv("OPENAI_API_BASE", "http://localhost:18000/v1")
API_KEY = os.getenv("OPENAI_API_KEY")
REQUEST_TIMEOUT = int(os.getenv("OPENAI_TIMEOUT", "60"))

DEFAULT_METADATA_KEYS = [
    "categories",
    "topics",
    "years",
    "dates",
    "events",
    "venues",
    "people",
]

app = FastAPI(title="OpenAI LLM Client Service")


class ChatRequest(BaseModel):
    prompt: str
    system: Optional[str] = Field(None, description="Optional system message")
    model: Optional[str] = Field(None, description="Model name override")
    temperature: float = Field(0.2, ge=0, le=2)
    max_tokens: int = Field(4096, gt=0)


class ChatResponse(BaseModel):
    model: str
    content: str
    usage: Optional[dict] = None


class MetadataRequest(BaseModel):
    text: str
    keys: Optional[List[str]] = Field(
        None, description="Which keys to extract; defaults to years/dates/events/venues/people/target_audience"
    )
    model: Optional[str] = None
    temperature: float = Field(0.1, ge=0, le=2)
    max_tokens: int = Field(4096, gt=0)


class MetadataResponse(BaseModel):
    model: str
    metadata: Dict[str, Any]
    raw: str
    usage: Optional[dict] = None


class RagContext(BaseModel):
    text: str
    score: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class RagRequest(BaseModel):
    question: str
    contexts: List[RagContext]
    model: Optional[str] = None
    temperature: float = Field(0.2, ge=0, le=2)
    max_tokens: int = Field(4096, gt=0)
    stream: bool = Field(False, description="Whether to stream the LLM response as SSE.")


class RagResponse(BaseModel):
    model: str
    answer: str
    usage: Optional[dict] = None


def _headers() -> dict:
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    return headers


def _chat(
    messages: List[Dict[str, str]],
    model: str,
    temperature: float,
    max_tokens: int,
) -> Dict:
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    resp = requests.post(
        f"{API_BASE}/chat/completions",
        headers=_headers(),
        json=payload,
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def _chat_stream(
    messages: List[Dict[str, str]],
    model: str,
    temperature: float,
    max_tokens: int,
):
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }
    with requests.post(
        f"{API_BASE}/chat/completions",
        headers=_headers(),
        json=payload,
        timeout=REQUEST_TIMEOUT,
        stream=True,
    ) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line:
                continue
            if line.startswith(b"data:"):
                line = line[5:].strip()
            data = line.strip()
            if not data or data == b"[DONE]":
                break
            try:
                chunk = json.loads(data.decode("utf-8"))
            except Exception:
                continue
            delta = (
                chunk.get("choices", [{}])[0]
                .get("delta", {})
                .get("content")
            )
            if delta:
                yield delta


def _parse_content(body: Dict) -> str:
    choices = body.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    return message.get("content", "") or ""


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    model = request.model or DEFAULT_MODEL
    messages = []
    if request.system:
        messages.append({"role": "system", "content": request.system})
    messages.append({"role": "user", "content": request.prompt})

    try:
        body = _chat(messages, model, request.temperature, request.max_tokens)
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Chat request failed: {exc}")
    except ValueError:
        raise HTTPException(status_code=500, detail="Invalid response from LLM provider")

    content = _parse_content(body)
    if not content:
        raise HTTPException(status_code=500, detail="Empty response from LLM provider")

    return ChatResponse(model=model, content=content, usage=body.get("usage"))


def _metadata_prompt(keys: List[str], text: str) -> List[Dict[str, str]]:
    key_list = ", ".join(keys)
    system = (
        "You are an information extraction & analytics assistant. "
        "Return a compact JSON object with the requested keys, "
        "leaving keys empty when no values are found."
    )
    user = (
        f"Extract the following keys from the content: {key_list}.\n"
        "For 'categories' key, provide a list of high-level categories that best describe the main topics of the content.\n"
        "Provide JSON only, no commentary.\n\n"
        f"Content:\n{text}"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _safe_json_parse(text: str) -> Dict[str, any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"unparsed": text}


@app.post("/metadata", response_model=MetadataResponse)
async def extract_metadata(request: MetadataRequest):
    keys = request.keys or DEFAULT_METADATA_KEYS
    model = request.model or DEFAULT_MODEL
    messages = _metadata_prompt(keys, request.text)

    try:
        body = _chat(messages, model, request.temperature, request.max_tokens)
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Metadata request failed: {exc}")
    except ValueError:
        raise HTTPException(status_code=500, detail="Invalid response from LLM provider")

    raw_content = _parse_content(body)
    metadata = _safe_json_parse(raw_content)
    
    print(f"Extracted metadata: {metadata}")

    return MetadataResponse(model=model, metadata=metadata, raw=raw_content, usage=body.get("usage"))


def _rag_messages(question: str, contexts: List[RagContext]) -> List[Dict[str, str]]:
    context_parts = []
    for idx, ctx in enumerate(contexts):
        meta_bits = []
        if ctx.metadata:
            for key in ["page_number", "chunk_index", "document_file_name"]:
                if key in ctx.metadata:
                    meta_bits.append(f"{key}={ctx.metadata[key]}")
        meta_str = f" ({', '.join(meta_bits)})" if meta_bits else ""
        score_str = f" [score={ctx.score}]" if ctx.score is not None else ""
        context_parts.append(f"[{idx+1}]{score_str}{meta_str}\n{ctx.text.strip()}")

    context_block = "\n\n".join(context_parts)
    system = (
        "You are a helpful assistant answering questions using only the provided context chunks. "
        "Be concise and cite relevant details. If the answer is not in the context, say you don't know."
    )
    user = f"Question: {question}\n\nContext:\n{context_block}"
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


@app.post("/rag", response_model=RagResponse)
async def rag_answer(request: RagRequest):
    model = request.model or DEFAULT_MODEL
    messages = _rag_messages(request.question, request.contexts)

    try:
        body = _chat(messages, model, request.temperature, request.max_tokens)
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"RAG request failed: {exc}")
    except ValueError:
        raise HTTPException(status_code=500, detail="Invalid response from LLM provider")

    content = _parse_content(body)
    if not content:
        raise HTTPException(status_code=500, detail="Empty response from LLM provider")

    return RagResponse(model=model, answer=content, usage=body.get("usage"))


@app.post("/rag/stream")
async def rag_answer_stream(request: RagRequest):
    model = request.model or DEFAULT_MODEL
    messages = _rag_messages(request.question, request.contexts)

    def event_stream():
        try:
            for token in _chat_stream(messages, model, request.temperature, request.max_tokens):
                yield f"data: {token}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as exc:
            yield f"data: [ERROR] {exc}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=16004)
