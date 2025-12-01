from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pymupdf4llm
import fitz  # PyMuPDF
import os
import tempfile
import shutil
import re
from collections import Counter

app = FastAPI(title="PyMuPDF Service", version="1.0.0")

# Configure CORS
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

@app.get("/health")
async def health_check():
    return {"status": "ok"}

STOPWORDS = {
    'the', 'and', 'that', 'with', 'this', 'from', 'there', 'have', 'will', 'shall', 'your', 'about', 'into', 'been',
    'were', 'would', 'could', 'should', 'their', 'them', 'these', 'those', 'here', 'such', 'than', 'then', 'over'
}


def _persist_pdf(upload: UploadFile) -> str:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        shutil.copyfileobj(upload.file, tmp_file)
        return tmp_file.name


def _convert_to_markdown(path: str) -> str:
    return pymupdf4llm.to_markdown(path)


def _convert_pages_to_markdown(doc: fitz.Document):
    """Return a {page_number: markdown} mapping."""
    per_page = {}
    for page_index in range(doc.page_count):
        try:
            markdown = pymupdf4llm.to_markdown(doc, page_numbers=[page_index])
        except Exception:
            markdown = ""
        markdown = (markdown or "").strip()
        if markdown:
            per_page[page_index + 1] = markdown
    return per_page


def _extract_headings(markdown: str, limit: int = 8):
    headings = []
    for line in markdown.splitlines():
        if line.strip().startswith('#'):
            title = line.lstrip('#').strip()
            if title:
                headings.append({"type": "heading", "value": title})
        if len(headings) >= limit:
            break
    return headings


def _extract_keywords(markdown: str, limit: int = 8):
    tokens = re.findall(r"[A-Za-z]{4,}", markdown.lower())
    filtered = [token for token in tokens if token not in STOPWORDS]
    if not filtered:
        return []
    counts = Counter(filtered)
    most_common = counts.most_common(limit)
    max_freq = most_common[0][1] if most_common else 1
    return [
        {"type": "keyword", "value": word, "score": round(freq / max_freq, 2)}
        for word, freq in most_common
    ]


def _document_metadata(doc: fitz.Document):
    metadata = {
        "page_count": doc.page_count,
        "title": doc.metadata.get("title"),
        "author": doc.metadata.get("author"),
        "subject": doc.metadata.get("subject"),
        "keywords": doc.metadata.get("keywords"),
    }
    return metadata


def _analyze_pdf(path: str):
    markdown = _convert_to_markdown(path)
    doc = fitz.open(path)
    try:
        metadata = _document_metadata(doc)
        entities = _extract_headings(markdown) + _extract_keywords(markdown)
        if metadata.get("page_count"):
            entities.append({"type": "page_count", "value": metadata["page_count"]})

        per_page_markdown = _convert_pages_to_markdown(doc)
        pages = []
        for page_index in range(doc.page_count):
            page = doc.load_page(page_index)
            text = page.get_text("text")
            entry = {"page": page_index + 1}
            if text and text.strip():
                entry["text"] = text
            page_markdown = per_page_markdown.get(page_index + 1)
            if page_markdown:
                entry["markdown"] = page_markdown
            if len(entry) > 1:
                pages.append(entry)

        return {"markdown": markdown, "metadata": metadata, "entities": entities, "pages": pages}
    finally:
        doc.close()


@app.post("/convert/pdf-to-markdown")
async def convert_pdf_to_markdown(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    tmp_path = _persist_pdf(file)

    try:
        md_text = _convert_to_markdown(tmp_path)
        return {"filename": file.filename, "markdown": md_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@app.post("/analyze/pdf")
async def analyze_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    tmp_path = _persist_pdf(file)

    try:
        analysis = _analyze_pdf(tmp_path)
        analysis["filename"] = file.filename
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=16002)
