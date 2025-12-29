"""
FastAPI application factory for the transcription web service.
"""

from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from .routes import api, websocket, pages


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title="Transcription Service",
        description="Web interface for audio/video transcription using Whisper",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )

    # Configure CORS for local development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins for local use
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Get paths relative to this file
    web_dir = Path(__file__).parent
    static_dir = web_dir / "static"
    templates_dir = web_dir / "templates"

    # Create directories if they don't exist
    static_dir.mkdir(parents=True, exist_ok=True)
    templates_dir.mkdir(parents=True, exist_ok=True)
    (static_dir / "css").mkdir(exist_ok=True)
    (static_dir / "js").mkdir(exist_ok=True)

    # Mount static files
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Set up templates
    templates = Jinja2Templates(directory=str(templates_dir))
    app.state.templates = templates

    # Include routers
    app.include_router(api.router, prefix="/api", tags=["API"])
    app.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])
    app.include_router(pages.router, tags=["Pages"])

    @app.on_event("startup")
    async def startup_event():
        """Initialize services on startup."""
        # Pre-initialize singleton services
        from .services.transcription_api import TranscriptionAPI
        from .services.job_manager import JobManager

        TranscriptionAPI()
        JobManager()

    return app


# Create app instance for uvicorn
app = create_app()
