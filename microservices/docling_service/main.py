"""Docling document-to-markdown service.

Exposes multi-format document parsing via Docling with configurable concurrency
and MLX acceleration on Apple Silicon.

Supported formats:
    - PDF, DOCX, PPTX, XLSX, HTML
    - Images: PNG, TIFF, JPEG
    - Audio: WAV, MP3 (via Whisper ASR)
    - VTT (WebVTT subtitles)

Environment variables:
    DOCLING_CONCURRENCY       max parallel requests; 0 = unlimited, 1 = serial (default: 1)
    DOCLING_CACHE_DIR         model cache directory (default: ~/.cache/docling)
    DOCLING_USE_OCR           enable OCR for PDFs (default: true)
    DOCLING_TABLE_STRUCTURE   enable table structure extraction (default: true)
    DOCLING_USE_MLX           use MLX acceleration on macOS (default: true)
    DOCLING_ASR_MODEL         Whisper model for audio transcription (default: base)
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
CONCURRENCY = int(os.getenv("DOCLING_CONCURRENCY", "1"))
CACHE_DIR = os.getenv("DOCLING_CACHE_DIR", str(Path.home() / ".cache" / "docling"))
USE_OCR = os.getenv("DOCLING_USE_OCR", "true").lower() in ("true", "1", "yes")
TABLE_STRUCTURE = os.getenv("DOCLING_TABLE_STRUCTURE", "true").lower() in ("true", "1", "yes")
USE_MLX = os.getenv("DOCLING_USE_MLX", "true").lower() in ("true", "1", "yes")
ASR_MODEL = os.getenv("DOCLING_ASR_MODEL", "base")  # tiny, base, small, medium, large

# Ensure cache dir exists
Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)
os.environ.setdefault("HF_HOME", CACHE_DIR)

# File extension mappings
PDF_EXTENSIONS = {".pdf"}
DOCX_EXTENSIONS = {".docx"}
PPTX_EXTENSIONS = {".pptx"}
XLSX_EXTENSIONS = {".xlsx"}
HTML_EXTENSIONS = {".html", ".htm", ".txt", ".md", ".rtf"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".tif"}
AUDIO_EXTENSIONS = {".wav", ".mp3"}
VTT_EXTENSIONS = {".vtt"}

ALL_SUPPORTED_EXTENSIONS = (
    PDF_EXTENSIONS | DOCX_EXTENSIONS | PPTX_EXTENSIONS | XLSX_EXTENSIONS |
    HTML_EXTENSIONS | IMAGE_EXTENSIONS | AUDIO_EXTENSIONS | VTT_EXTENSIONS
)

# ---------------------------------------------------------------------------
# Lazy-load Docling to avoid slow import at module level
# ---------------------------------------------------------------------------
_docling_loaded = False
_converter = None
_audio_converter = None


def _ensure_docling():
    global _docling_loaded, _converter, _audio_converter
    if _docling_loaded:
        return
    
    from docling.document_converter import (
        DocumentConverter,
        PdfFormatOption,
        WordFormatOption,
        PowerpointFormatOption,
        HTMLFormatOption,
        ImageFormatOption,
    )
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    
    # Configure PDF pipeline
    pdf_options = PdfPipelineOptions()
    pdf_options.do_ocr = USE_OCR
    pdf_options.do_table_structure = TABLE_STRUCTURE
    
    # Build format options
    format_options = {
        InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options),
        InputFormat.DOCX: WordFormatOption(),
        InputFormat.PPTX: PowerpointFormatOption(),
        InputFormat.HTML: HTMLFormatOption(),
        InputFormat.IMAGE: ImageFormatOption(),
    }
    
    # Try to add Excel support (may not be available in all versions)
    try:
        from docling.document_converter import ExcelFormatOption
        format_options[InputFormat.XLSX] = ExcelFormatOption()
    except ImportError:
        pass
    
    _converter = DocumentConverter(format_options=format_options)
    
    # Try to set up audio converter with ASR pipeline
    try:
        from docling.document_converter import AudioFormatOption
        from docling.datamodel.pipeline_options import AsrPipelineOptions
        from docling.datamodel import asr_model_specs
        from docling.pipeline.asr_pipeline import AsrPipeline
        
        # Select ASR model based on config and MLX preference
        asr_options = None
        if USE_MLX:
            asr_options = getattr(asr_model_specs, f"WHISPER_{ASR_MODEL.upper()}_MLX", None)
        if not asr_options:
            asr_options = getattr(asr_model_specs, f"WHISPER_{ASR_MODEL.upper()}", None)
        
        if asr_options:
            pipeline_options = AsrPipelineOptions(asr_options=asr_options)
            _audio_converter = DocumentConverter(
                format_options={
                    InputFormat.AUDIO: AudioFormatOption(
                        pipeline_cls=AsrPipeline,
                        pipeline_options=pipeline_options,
                    )
                }
            )
    except ImportError:
        _audio_converter = None
    
    _docling_loaded = True


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="Docling Service", version="1.0.0")

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

# Thread pool for blocking Docling calls
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
class TableData(BaseModel):
    rows: int
    columns: int
    markdown: Optional[str] = None
    html: Optional[str] = None


class ContentBlock(BaseModel):
    type: str  # text, table, picture, formula, etc.
    text: Optional[str] = None
    html: Optional[str] = None
    table: Optional[TableData] = None
    metadata: Optional[Dict[str, Any]] = None


class PageResult(BaseModel):
    page: int
    blocks: Optional[List[ContentBlock]] = None


class AnalyzeResponse(BaseModel):
    filename: str
    format: str
    markdown: str
    html: Optional[str] = None
    pages: List[PageResult]
    tables: List[TableData]
    metadata: Optional[Dict[str, Any]] = None


class ConvertResponse(BaseModel):
    filename: str
    format: str
    markdown: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_file_format(filename: str) -> str:
    """Return format category from filename extension."""
    ext = Path(filename).suffix.lower()
    if ext in PDF_EXTENSIONS:
        return "pdf"
    elif ext in DOCX_EXTENSIONS:
        return "docx"
    elif ext in PPTX_EXTENSIONS:
        return "pptx"
    elif ext in XLSX_EXTENSIONS:
        return "xlsx"
    elif ext in HTML_EXTENSIONS:
        return "html"
    elif ext in IMAGE_EXTENSIONS:
        return "image"
    elif ext in AUDIO_EXTENSIONS:
        return "audio"
    elif ext in VTT_EXTENSIONS:
        return "vtt"
    return "unknown"


def _persist_upload(upload: UploadFile) -> str:
    """Save uploaded file to temp location and return path."""
    suffix = Path(upload.filename or "file").suffix or ".pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(upload.file, tmp)
        return tmp.name


def _parse_vtt(path: str) -> Dict[str, Any]:
    """Parse WebVTT subtitle file to markdown."""
    lines = []
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Simple VTT parser - extract text content
    in_cue = False
    cue_text = []
    
    for line in content.split("\n"):
        line = line.strip()
        
        # Skip WEBVTT header and metadata
        if line.startswith("WEBVTT") or line.startswith("NOTE"):
            continue
        
        # Timestamp line marks start of cue
        if "-->" in line:
            in_cue = True
            continue
        
        # Empty line ends cue
        if not line:
            if cue_text:
                lines.append(" ".join(cue_text))
                cue_text = []
            in_cue = False
            continue
        
        # Collect cue text
        if in_cue:
            # Strip VTT formatting tags
            import re
            clean = re.sub(r"<[^>]+>", "", line)
            if clean:
                cue_text.append(clean)
    
    # Add any remaining cue text
    if cue_text:
        lines.append(" ".join(cue_text))
    
    markdown = "\n\n".join(lines)
    
    return {
        "markdown": markdown,
        "html": None,
        "pages": [],
        "tables": [],
        "metadata": {"format": "vtt", "cue_count": len(lines)},
    }


def _run_docling(path: str, filename: str) -> Dict[str, Any]:
    """Blocking call to Docling parser. Returns dict with markdown + structured data."""
    _ensure_docling()
    
    file_format = _get_file_format(filename)
    
    # Handle VTT separately (not supported by Docling)
    if file_format == "vtt":
        return _parse_vtt(path)
    
    # Handle audio files
    if file_format == "audio":
        if _audio_converter is None:
            raise ValueError("Audio transcription not available. Install docling with ASR support.")
        result = _audio_converter.convert(path)
        markdown = result.document.export_to_markdown()
        return {
            "markdown": markdown,
            "html": None,
            "pages": [],
            "tables": [],
            "metadata": {"format": "audio", "status": str(result.status)},
        }
    
    # Convert document using Docling
    result = _converter.convert(path)
    doc = result.document
    
    # Export to various formats
    markdown = doc.export_to_markdown()
    
    try:
        html = doc.export_to_html()
    except Exception:
        html = None
    
    # Extract tables
    tables: List[Dict[str, Any]] = []
    try:
        for table in doc.tables:
            df = table.export_to_dataframe()
            tables.append({
                "rows": len(df),
                "columns": len(df.columns),
                "markdown": df.to_markdown(),
                "html": df.to_html(),
            })
    except Exception:
        pass
    
    # Build page structure
    pages: List[Dict[str, Any]] = []
    try:
        from docling_core.types.doc.document import TextItem, TableItem
        
        page_map: Dict[int, Dict[str, Any]] = {}
        
        for item, level in doc.iterate_items():
            # Get page number from provenance if available
            page_num = 1  # Default
            if hasattr(item, "prov") and item.prov:
                for prov in item.prov:
                    if hasattr(prov, "page_no"):
                        page_num = prov.page_no
                        break
            
            if page_num not in page_map:
                page_map[page_num] = {"page": page_num, "blocks": []}
            
            block: Dict[str, Any] = {"type": "unknown", "metadata": {"level": level}}
            
            if isinstance(item, TextItem):
                block["type"] = "text"
                block["text"] = item.text
            elif isinstance(item, TableItem):
                block["type"] = "table"
                try:
                    df = item.export_to_dataframe()
                    block["table"] = {
                        "rows": len(df),
                        "columns": len(df.columns),
                        "markdown": df.to_markdown(),
                        "html": df.to_html(),
                    }
                except Exception:
                    block["text"] = str(item)
            else:
                block["type"] = type(item).__name__.lower()
                if hasattr(item, "text"):
                    block["text"] = item.text
            
            page_map[page_num]["blocks"].append(block)
        
        pages = sorted(page_map.values(), key=lambda p: p["page"])
    except Exception:
        # Fallback: single page with all content
        pages = [{"page": 1, "blocks": [{"type": "text", "text": markdown}]}]
    
    return {
        "markdown": markdown,
        "html": html,
        "pages": pages,
        "tables": tables,
        "metadata": {
            "format": file_format,
            "status": str(result.status),
        },
    }


async def _parse_file(upload: UploadFile) -> Dict[str, Any]:
    """Async wrapper for Docling parsing."""
    # Validate file extension
    filename = upload.filename or "file.pdf"
    ext = Path(filename).suffix.lower()
    
    if ext not in ALL_SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file format: {ext}. "
            f"Supported: {', '.join(sorted(ALL_SUPPORTED_EXTENSIONS))}"
        )
    
    tmp_path = _persist_upload(upload)
    loop = asyncio.get_running_loop()

    async def do_parse():
        return await loop.run_in_executor(_executor, _run_docling, tmp_path, filename)

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
    return {
        "status": "ok",
        "concurrency": CONCURRENCY,
        "ocr_enabled": USE_OCR,
        "table_structure": TABLE_STRUCTURE,
        "mlx_enabled": USE_MLX,
        "supported_formats": sorted(ALL_SUPPORTED_EXTENSIONS),
    }


@app.post("/convert/to-markdown", response_model=ConvertResponse)
async def convert_to_markdown(file: UploadFile = File(...)):
    """Convert document to markdown. Returns only the markdown output."""
    try:
        result = await _parse_file(file)
        return ConvertResponse(
            filename=file.filename or "unknown",
            format=_get_file_format(file.filename or "unknown"),
            markdown=result["markdown"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(file: UploadFile = File(...)):
    """Analyze document. Returns markdown + per-page blocks + tables + metadata."""
    try:
        result = await _parse_file(file)
        
        pages = [
            PageResult(
                page=p["page"],
                blocks=[ContentBlock(
                    type=b.get("type", "unknown"),
                    text=b.get("text"),
                    html=b.get("html"),
                    table=TableData(**b["table"]) if b.get("table") else None,
                    metadata=b.get("metadata"),
                ) for b in p.get("blocks", [])],
            )
            for p in result.get("pages", [])
        ]
        
        tables = [TableData(**t) for t in result.get("tables", [])]
        
        return AnalyzeResponse(
            filename=file.filename or "unknown",
            format=_get_file_format(file.filename or "unknown"),
            markdown=result["markdown"],
            html=result.get("html"),
            pages=pages,
            tables=tables,
            metadata=result.get("metadata"),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=16008)
