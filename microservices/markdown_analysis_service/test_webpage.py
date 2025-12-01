"""Test webpage for Markdown Analysis Service.

Provides an HTML UI at /test for testing document analysis with SSE streaming.

This module serves as the router/controller, delegating template rendering
to the modular templates package for separation of concerns.
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from templates import build_html_page

router = APIRouter()


@router.get("/test", response_class=HTMLResponse)
async def test_page():
    """Serve the test webpage."""
    return build_html_page()

