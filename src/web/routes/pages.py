"""
HTML page routes for the web UI.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main transcription page."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": "Transcription Service",
            "active_page": "transcribe",
        },
    )


@router.get("/history", response_class=HTMLResponse)
async def history(request: Request):
    """Transcription history page."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "history.html",
        {
            "request": request,
            "title": "History - Transcription Service",
            "active_page": "history",
        },
    )
