import re
from typing import Any, Dict, List, Optional, Sequence

from fastapi import FastAPI, HTTPException
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import BaseModel, Field

app = FastAPI()

_CJK_REGEX = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
ENGLISH_SEPARATORS = [
    "\n\n",
    "\n",
    ". ",
    ".\n",
    "? ",
    "?\n",
    "! ",
    "!\n",
    "; ",
    ";\n",
    ", ",
    ",\n",
    " ",
    "",
]
CHINESE_SEPARATORS = [
    "\n\n",
    "\n",
    "。",  # full stop
    "！",
    "？",
    "；",
    "，",
    "：",
    "、",
    " ",
    "",
]


class ChunkingRequest(BaseModel):
    text: str = Field(..., description="Full text to chunk")
    chunk_size: int = Field(1000, gt=0, description="Target size of each chunk")
    chunk_overlap: int = Field(200, ge=0, description="Overlap between chunks")
    language_hint: Optional[str] = Field(
        None, description="Optional language hint such as 'english' or 'chinese'"
    )
    separators: Optional[List[str]] = Field(
        None,
        description="Custom separators to override defaults; will be tried in order",
    )
    keep_separator: bool = Field(
        True,
        description="Whether to keep separators at the end of the previous chunk",
    )
    metadata: Optional[Dict[str, Any]] = None


class Chunk(BaseModel):
    text: str
    metadata: Dict[str, Any]


class ChunkingResponse(BaseModel):
    chunks: List[Chunk]


def _contains_cjk(text: str) -> bool:
    return bool(_CJK_REGEX.search(text))


def _build_separators(
    language_hint: Optional[str], text: str, custom: Optional[Sequence[str]]
) -> List[str]:
    if custom:
        separators = list(custom)
        if separators[-1] != "":
            separators.append("")
        return separators

    hint = (language_hint or "").lower()
    if hint in {"zh", "zh-cn", "chinese", "cn"} or _contains_cjk(text):
        return CHINESE_SEPARATORS
    return ENGLISH_SEPARATORS


def create_text_splitter(request: ChunkingRequest) -> RecursiveCharacterTextSplitter:
    separators = _build_separators(request.language_hint, request.text, request.separators)
    return RecursiveCharacterTextSplitter(
        chunk_size=request.chunk_size,
        chunk_overlap=request.chunk_overlap,
        separators=separators,
        length_function=len,
        keep_separator=request.keep_separator,
        is_separator_regex=False,
    )


def perform_chunking(request: ChunkingRequest) -> ChunkingResponse:
    text_splitter = create_text_splitter(request)
    docs = text_splitter.create_documents(
        [request.text], metadatas=[request.metadata] if request.metadata else None
    )

    chunks = []
    for i, doc in enumerate(docs):
        chunk_metadata = doc.metadata.copy() if doc.metadata else {}
        chunk_metadata["chunk_index"] = i
        chunks.append(Chunk(text=doc.page_content, metadata=chunk_metadata))

    return ChunkingResponse(chunks=chunks)


@app.post("/chunk", response_model=ChunkingResponse)
async def chunk_text(request: ChunkingRequest):
    try:
        return perform_chunking(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=16006)
