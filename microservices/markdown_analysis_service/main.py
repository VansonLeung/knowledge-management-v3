"""Markdown Analysis Service - Agentic text analysis with LLM.

FastAPI service that uses OpenAI-compatible API with function calling
to analyze text documents. The LLM agent iteratively uses tools to
read, clean, and extract structured information.

Modules:
    config      - Environment and settings management
    models      - Pydantic request/response schemas
    tools       - LLM tool definitions for function calling
    state       - Analysis state management
    prompts     - System prompt generation
    analysis    - Main analysis engine with SSE streaming
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from analysis import (
    analyze_document_stream,
    evaluate_article_cleanliness,
    polish_content,
    finalize_content,
    glossary_lookup,
)
from config import ServiceConfig
from models import (
    StudyTextRequest,
    EvaluateCleanlinessRequest,
    PolishContentRequest,
    FinalizeContentRequest,
    GlossaryLookupRequest,
)


# ---------------------------------------------------------------------------
# Initialize Environment
# ---------------------------------------------------------------------------
serviceConfig = ServiceConfig.from_env()

print(
    f"Markdown Analysis Service starting with "
    f"model={serviceConfig.model}, "
    f"base_url={serviceConfig.base_url}, "
    f"max_iterations={serviceConfig.max_iterations}, "
    f"max_keywords={serviceConfig.max_keywords}"
)


# ---------------------------------------------------------------------------
# FastAPI Application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Markdown Analysis Service",
    description="Agentic text analysis with LLM function calling",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount test webpage router
try:
    from test_webpage import router as test_router
    app.include_router(test_router)
except ImportError:
    pass


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------
@app.post("/study_text")
async def study_text(request: StudyTextRequest):
    """Analyze text content using LLM with agentic tool use.
    
    Performs iterative analysis using function calling to:
    - Read and understand document structure
    - Remove noise (headers, footers, page numbers)
    - Extract named sections
    - Look up glossary terms
    - Generate keywords and categorize
    
    Returns a Server-Sent Events stream with progress updates.
    """
    return StreamingResponse(
        analyze_document_stream(request, serviceConfig),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/health")
async def health():
    """Health check endpoint with configuration info."""
    return {
        "status": "ok",
        "model": serviceConfig.model,
        "max_iterations": serviceConfig.max_iterations,
        "max_keywords": serviceConfig.max_keywords,
    }


@app.post("/evaluate_article_cleanliness")
async def evaluate_cleanliness(request: EvaluateCleanlinessRequest):
    """Evaluate whether an article's text is clean or messy.
    
    Chunks the input text and prompts an LLM to evaluate cleanliness.
    Returns a JSON response indicating whether the article needs cleaning.
    
    Returns:
        JSON with is_messy boolean, cleanliness_score, reasoning, and issues_found.
    """
    return await evaluate_article_cleanliness(request, serviceConfig)


@app.post("/polish_content")
async def polish_content_endpoint(request: PolishContentRequest):
    """Polish and clean article content.
    
    Removes web artifacts, fixes formatting, and cleans up messy text
    while preserving the original meaning and important information.
    
    Returns:
        JSON with polished_content, changes_made, and sections_removed.
    """
    return await polish_content(request, serviceConfig)


@app.post("/finalize_content")
async def finalize_content_endpoint(request: FinalizeContentRequest):
    """Finalize content by extracting metadata and classification.
    
    Analyzes the text to extract language, title, summary, keywords,
    category, author info, and other metadata.
    
    Returns:
        JSON with language, title, summary, keywords, category, and metadata.
    """
    return await finalize_content(request, serviceConfig)


@app.post("/glossary_lookup")
async def glossary_lookup_endpoint(request: GlossaryLookupRequest):
    """Look up glossary terms in the text.
    
    Searches for occurrences of glossary terms in the provided text
    and returns matches with occurrence counts.
    
    Returns:
        JSON with matches array containing term, occurrences, and definition.
    """
    return await glossary_lookup(request, serviceConfig)


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=16009)
