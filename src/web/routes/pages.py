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
        },
    )
