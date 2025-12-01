"""MinerU document-to-markdown/JSON service.

Exposes PDF/image parsing via MinerU with configurable concurrency and MLX
acceleration on Apple Silicon.

Environment variables:
    MINERU_BACKEND        vlm-mlx-engine | vlm-transformers | pipeline (default: vlm-mlx-engine)
    MINERU_CONCURRENCY    max parallel requests; 0 = unlimited, 1 = serial (default: 1)
    MINERU_CACHE_DIR      model cache directory (default: ~/.cache/mineru)
"""

from __future__ import annotations

import asyncio
import os
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BACKEND = os.getenv("MINERU_BACKEND", "vlm-mlx-engine")
CONCURRENCY = int(os.getenv("MINERU_CONCURRENCY", "1"))
CACHE_DIR = os.getenv("MINERU_CACHE_DIR", str(Path.home() / ".cache" / "mineru"))
OUTPUT_DIR = os.getenv("MINERU_OUTPUT_DIR", "")  # Empty = use temp directory

# Ensure cache dir exists
Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)
os.environ.setdefault("HF_HOME", CACHE_DIR)
os.environ.setdefault("MINERU_CACHE_DIR", CACHE_DIR)

# Ensure output dir exists (if configured)
if OUTPUT_DIR:
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Lazy-load MinerU to avoid slow import at module level
# ---------------------------------------------------------------------------
_mineru_loaded = False


def _ensure_mineru():
    global _mineru_loaded
    if _mineru_loaded:
        return
    # Import here so startup is fast; heavy model load happens on first call
    import mineru  # noqa: F401

    _mineru_loaded = True


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="MinerU Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount test webpage
try:
    from test_webpage import router as test_router
    app.include_router(test_router)
except ImportError:
    pass  # test_webpage not available

# Thread pool for blocking MinerU calls (size = CONCURRENCY, or None for unlimited)
_executor: Optional[ThreadPoolExecutor] = None
_semaphore: Optional[asyncio.Semaphore] = None


@app.on_event("startup")
async def _startup():
    global _executor, _semaphore
    max_workers = CONCURRENCY if CONCURRENCY > 0 else None
    _executor = ThreadPoolExecutor(max_workers=max_workers)
    if CONCURRENCY > 0:
        _semaphore = asyncio.Semaphore(CONCURRENCY)


@app.on_event("shutdown")
async def _shutdown():
    if _executor:
        _executor.shutdown(wait=False)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class ContentBlock(BaseModel):
    type: str
    text: Optional[str] = None
    latex: Optional[str] = None
    html: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class PageResult(BaseModel):
    page: int
    markdown: Optional[str] = None
    blocks: Optional[List[ContentBlock]] = None


class AnalyzeResponse(BaseModel):
    filename: str
    markdown: str
    pages: List[PageResult]
    metadata: Optional[Dict[str, Any]] = None


class ConvertResponse(BaseModel):
    filename: str
    markdown: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _persist_upload(upload: UploadFile) -> str:
    suffix = Path(upload.filename or "file").suffix or ".pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(upload.file, tmp)
        return tmp.name


def _run_mineru(path: str) -> Dict[str, Any]:
    """Blocking call to MinerU parser. Returns dict with markdown + structured data."""
    _ensure_mineru()

    from mineru.cli.common import read_fn, do_parse
    import json

    # Read file bytes (handles PDF and images)
    pdf_bytes = read_fn(path)
    filename = Path(path).stem

    # Create output directory (use temp if OUTPUT_DIR not configured)
    import uuid
    job_id = uuid.uuid4().hex[:8]
    if OUTPUT_DIR:
        output_dir = str(Path(OUTPUT_DIR) / f"{filename}_{job_id}")
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        use_temp = False
    else:
        output_dir = tempfile.mkdtemp(prefix=f"mineru_{filename}_{job_id}_")
        use_temp = True

    print(f"Output directory: {output_dir}")
    print(f"Files: {os.listdir(output_dir)}")

    try:
        # Run MinerU parsing
        do_parse(
            output_dir=output_dir,
            pdf_file_names=[filename],
            pdf_bytes_list=[pdf_bytes],
            p_lang_list=["ch"],  # auto-detect language
            backend=BACKEND,
            parse_method="auto",
            formula_enable=True,
            table_enable=True,
            f_draw_layout_bbox=False,
            f_draw_span_bbox=False,
            f_dump_md=True,
            f_dump_middle_json=False,
            f_dump_model_output=False,
            f_dump_orig_pdf=False,
            f_dump_content_list=True,
        )
        
        print("MinerU parsing completed.")

        # Read output files
        result_dir = Path(output_dir) / filename / "vlm"
        markdown = ""
        content_list = []

        # Read markdown
        md_files = list(result_dir.glob("*.md"))
        if md_files:
            markdown = md_files[0].read_text(encoding="utf-8")

        # Read content_list.json if available
        content_list_path = result_dir / "content_list.json"
        if content_list_path.exists():
            content_list = json.loads(content_list_path.read_text(encoding="utf-8"))

        # Build per-page breakdown
        pages: List[Dict[str, Any]] = []
        page_map: Dict[int, Dict[str, Any]] = {}
        for block in content_list:
            page_num = block.get("page_idx", 0) + 1  # 0-indexed in content_list
            if page_num not in page_map:
                page_map[page_num] = {"page": page_num, "blocks": []}
            page_map[page_num]["blocks"].append({
                "type": block.get("type", "unknown"),
                "text": block.get("text", ""),
                "latex": block.get("latex"),
                "html": block.get("html"),
                "metadata": {k: v for k, v in block.items() if k not in ("type", "text", "latex", "html", "page_idx")},
            })
        pages = sorted(page_map.values(), key=lambda p: p["page"])

        return {
            "markdown": markdown,
            "pages": pages,
            "metadata": None,
            "output_dir": output_dir,
        }
    except Exception:
        # Cleanup on error
        shutil.rmtree(output_dir, ignore_errors=True)
        raise
    finally:
        # Cleanup temp directory after processing
        if use_temp:
            shutil.rmtree(output_dir, ignore_errors=True)


async def _parse_file(upload: UploadFile) -> Dict[str, Any]:
    tmp_path = _persist_upload(upload)
    loop = asyncio.get_running_loop()

    async def do_parse():
        return await loop.run_in_executor(_executor, _run_mineru, tmp_path)

    try:
        if _semaphore:
            async with _semaphore:
                return await do_parse()
        else:
            return await do_parse()
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok", "backend": BACKEND, "concurrency": CONCURRENCY}


@app.post("/convert/to-markdown", response_model=ConvertResponse)
async def convert_to_markdown(file: UploadFile = File(...)):
    """Return only the markdown output."""
    try:
        result = await _parse_file(file)
        return ConvertResponse(filename=file.filename or "unknown", markdown=result["markdown"])
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(file: UploadFile = File(...)):
    """Return markdown + per-page structured blocks + metadata."""
    try:
        result = await _parse_file(file)
        pages = [
            PageResult(
                page=p["page"],
                markdown=None,
                blocks=[ContentBlock(**b) for b in p.get("blocks", [])],
            )
            for p in result.get("pages", [])
        ]
        return AnalyzeResponse(
            filename=file.filename or "unknown",
            markdown=result["markdown"],
            pages=pages,
            metadata=result.get("metadata"),
        )
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=16007)
