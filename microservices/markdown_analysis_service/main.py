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

from analysis import analyze_document_stream
from config import ServiceConfig
from models import StudyTextRequest


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


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=16009)
