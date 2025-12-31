"""
REST API endpoints for batch transcription.
"""

import asyncio
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse

from ..services.transcription_api import TranscriptionAPI
from ..services.job_manager import JobManager, JobStatus, run_transcription_job
from ..services.history_manager import HistoryManager
from ..services.vocabulary_manager import VocabularyManager
from ..services.url_downloader import URLDownloader
from ..services.translation_service import TranslationService
from ..models.responses import (
    HealthResponse,
    InfoResponse,
    ModelInfo,
    JobResponse,
    TranscriptionResultResponse,
    SegmentResponse,
    ErrorResponse,
)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.now(),
    )


@router.get("/info", response_model=InfoResponse)
async def get_info():
    """Get system information."""
    api = TranscriptionAPI()

    models = [
        ModelInfo(**model_info)
        for model_info in api.get_available_models()
    ]

    return InfoResponse(
        version="1.0.0",
        supported_formats=api.get_supported_formats(),
        available_models=models,
        output_formats=api.get_output_formats(),
        features={
            "speaker_detection": True,
            "audio_preprocessing": True,
            "streaming": True,
            "batch_processing": True,
        },
    )


@router.get("/formats")
async def get_formats():
    """Get supported input formats."""
    api = TranscriptionAPI()
    return api.get_supported_formats()


@router.get("/models")
async def get_models():
    """Get available Whisper models."""
    api = TranscriptionAPI()
    return api.get_available_models()


@router.post("/transcribe")
async def transcribe_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    output_format: str = Form(default="json"),
    model: str = Form(default="base"),
    language: Optional[str] = Form(default=None),
    enable_speakers: bool = Form(default=False),
    num_speakers: Optional[int] = Form(default=None),
    enable_preprocessing: bool = Form(default=False),
    show_timestamps: bool = Form(default=False),
    use_vocabulary: bool = Form(default=False),
    async_mode: bool = Form(default=True),
):
    """
    Upload and transcribe an audio/video file.

    For async_mode=True (default), returns job ID immediately.
    For async_mode=False, waits for completion and returns result.
    """
    api = TranscriptionAPI()
    job_manager = JobManager()

    # Validate file extension
    supported_formats = api.get_supported_formats()
    all_formats = supported_formats["audio"] + supported_formats["video"]

    filename = file.filename or "upload"
    ext = "." + filename.split(".")[-1].lower() if "." in filename else ""

    if ext not in all_formats:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: {ext}. Supported: {all_formats}",
        )

    # Read and save uploaded file
    file_content = await file.read()
    temp_path = await api.save_upload_file(file_content, filename)

    # Create transcription settings
    settings = {
        "output_format": output_format,
        "model": model,
        "language": language,
        "enable_speakers": enable_speakers,
        "num_speakers": num_speakers,
        "enable_preprocessing": enable_preprocessing,
        "show_timestamps": show_timestamps,
        "use_vocabulary": use_vocabulary,
    }

    if async_mode:
        # Create job and run in background
        job = await job_manager.create_job(
            filename=filename,
            file_path=temp_path,
            settings=settings,
        )

        # Define transcription function
        async def transcribe():
            try:
                result = await api.transcribe_file(
                    file_path=temp_path,
                    **settings,
                )
                return result
            finally:
                api.cleanup_temp_file(temp_path)

        # Run in background
        background_tasks.add_task(
            run_transcription_job,
            job.job_id,
            transcribe,
            job_manager,
        )

        return {
            "job_id": job.job_id,
            "status": "queued",
            "message": f"Transcription job created for {filename}",
        }

    else:
        # Synchronous mode - wait for result
        try:
            result = await api.transcribe_file(
                file_path=temp_path,
                **settings,
            )

            if not result.get("success"):
                raise HTTPException(
                    status_code=500,
                    detail=result.get("error", "Transcription failed"),
                )

            # Save to history
            try:
                history_manager = HistoryManager()
                history_manager.save_transcription(result, filename)
            except Exception as hist_err:
                print(f"Warning: Failed to save to history: {hist_err}")

            # Format segments
            segments = [
                SegmentResponse(
                    start=seg.get("start", 0),
                    end=seg.get("end", 0),
                    text=seg.get("text", ""),
                    confidence=seg.get("confidence"),
                    speaker=seg.get("speaker"),
                )
                for seg in result.get("segments", [])
            ]

            return {
                "success": True,
                "text": result.get("text", ""),
                "language": result.get("language", "unknown"),
                "confidence": result.get("confidence", 0),
                "word_count": result.get("word_count", 0),
                "processing_time": result.get("processing_time", 0),
                "segments": [s.model_dump() for s in segments],
            }

        finally:
            api.cleanup_temp_file(temp_path)


@router.post("/transcribe/url")
async def transcribe_url(
    background_tasks: BackgroundTasks,
    url: str = Form(...),
    output_format: str = Form(default="json"),
    model: str = Form(default="base"),
    language: Optional[str] = Form(default=None),
    enable_speakers: bool = Form(default=False),
    num_speakers: Optional[int] = Form(default=None),
    enable_preprocessing: bool = Form(default=False),
    show_timestamps: bool = Form(default=False),
    use_vocabulary: bool = Form(default=False),
):
    """
    Download and transcribe audio from a YouTube or Vimeo URL.
    Returns job ID immediately and processes in background.
    """
    api = TranscriptionAPI()
    job_manager = JobManager()
    downloader = URLDownloader()

    # Validate URL
    if not downloader.is_supported_url(url):
        raise HTTPException(
            status_code=400,
            detail="Unsupported URL. Only YouTube and Vimeo URLs are supported.",
        )

    # Get video info first
    info = downloader.get_video_info(url)
    if not info.get("success"):
        raise HTTPException(
            status_code=400,
            detail=info.get("error", "Failed to get video information"),
        )

    # Create transcription settings
    settings = {
        "output_format": output_format,
        "model": model,
        "language": language,
        "enable_speakers": enable_speakers,
        "num_speakers": num_speakers,
        "enable_preprocessing": enable_preprocessing,
        "show_timestamps": show_timestamps,
        "use_vocabulary": use_vocabulary,
    }

    # Create job with video title as filename
    filename = info.get("filename", "url_download.wav")
    job = await job_manager.create_job(
        filename=filename,
        file_path="",  # Will be set after download
        settings=settings,
    )

    # Define download and transcribe function
    async def download_and_transcribe():
        try:
            # Download audio
            download_result = downloader.download_audio(url)
            if not download_result.get("success"):
                return {"success": False, "error": download_result.get("error")}

            temp_path = download_result["file_path"]

            try:
                # Filter out display-only options that transcribe_file doesn't accept
                transcribe_settings = {
                    k: v for k, v in settings.items()
                    if k not in ("show_timestamps",)
                }
                # Transcribe
                result = await api.transcribe_file(
                    file_path=temp_path,
                    **transcribe_settings,
                )
                return result
            finally:
                # Cleanup downloaded file
                downloader.cleanup(temp_path)

        except Exception as e:
            return {"success": False, "error": str(e)}

    # Run in background
    background_tasks.add_task(
        run_transcription_job,
        job.job_id,
        download_and_transcribe,
        job_manager,
    )

    return {
        "job_id": job.job_id,
        "status": "queued",
        "message": f"Transcription job created for: {info.get('title', url)}",
        "video_info": {
            "title": info.get("title"),
            "duration": info.get("duration"),
            "uploader": info.get("uploader"),
        },
    }


@router.get("/url/info")
async def get_url_info(url: str):
    """Get information about a video URL without downloading."""
    downloader = URLDownloader()

    if not downloader.is_supported_url(url):
        raise HTTPException(
            status_code=400,
            detail="Unsupported URL. Only YouTube and Vimeo URLs are supported.",
        )

    info = downloader.get_video_info(url)
    if not info.get("success"):
        raise HTTPException(
            status_code=400,
            detail=info.get("error", "Failed to get video information"),
        )

    return info


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str):
    """Get the status of a transcription job."""
    job_manager = JobManager()
    job = await job_manager.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    return JobResponse(
        job_id=job.job_id,
        status=job.status.value,
        progress=job.progress,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error=job.error,
        filename=job.filename,
    )


@router.get("/jobs/{job_id}/result")
async def get_job_result(job_id: str):
    """Get the result of a completed transcription job."""
    job_manager = JobManager()
    job = await job_manager.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    if job.status == JobStatus.QUEUED:
        raise HTTPException(status_code=400, detail="Job is still queued")

    if job.status == JobStatus.PROCESSING:
        raise HTTPException(status_code=400, detail="Job is still processing")

    if job.status == JobStatus.FAILED:
        raise HTTPException(status_code=500, detail=job.error or "Job failed")

    if not job.result:
        raise HTTPException(status_code=500, detail="No result available")

    result = job.result

    # Format segments
    segments = [
        {
            "start": seg.get("start", 0),
            "end": seg.get("end", 0),
            "text": seg.get("text", ""),
            "confidence": seg.get("confidence"),
            "speaker": seg.get("speaker"),
        }
        for seg in result.get("segments", [])
    ]

    return {
        "job_id": job_id,
        "success": result.get("success", True),
        "text": result.get("text", ""),
        "language": result.get("language", "unknown"),
        "confidence": result.get("confidence", 0),
        "word_count": result.get("word_count", 0),
        "processing_time": result.get("processing_time", 0),
        "segments": segments,
        "speaker_detection": result.get("speaker_detection"),
    }


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a transcription job."""
    job_manager = JobManager()
    api = TranscriptionAPI()

    job = await job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    # Clean up temp file
    api.cleanup_temp_file(job.file_path)

    # Delete job
    await job_manager.delete_job(job_id)

    return {"message": f"Job {job_id} deleted"}


@router.get("/jobs")
async def list_jobs(limit: int = 50):
    """List recent transcription jobs."""
    job_manager = JobManager()
    jobs = await job_manager.list_jobs(limit=limit)

    return [
        {
            "job_id": job.job_id,
            "status": job.status.value,
            "progress": job.progress,
            "created_at": job.created_at.isoformat(),
            "filename": job.filename,
        }
        for job in jobs
    ]


# ============================================================================
# History Endpoints
# ============================================================================

@router.get("/history")
async def get_history(limit: int = 50, offset: int = 0):
    """Get paginated transcription history."""
    history_manager = HistoryManager()
    entries = history_manager.get_history(limit=limit, offset=offset)
    stats = history_manager.get_stats()

    return {
        "entries": entries,
        "total": stats["total_entries"],
        "limit": limit,
        "offset": offset,
    }


@router.get("/history/search")
async def search_history(q: str, limit: int = 50):
    """Search transcription history using full-text search."""
    if not q or len(q) < 2:
        raise HTTPException(status_code=400, detail="Search query must be at least 2 characters")

    history_manager = HistoryManager()
    entries = history_manager.search_history(query=q, limit=limit)

    return {
        "entries": entries,
        "query": q,
        "count": len(entries),
    }


@router.get("/history/stats")
async def get_history_stats():
    """Get history statistics."""
    history_manager = HistoryManager()
    return history_manager.get_stats()


@router.get("/history/{entry_id}")
async def get_history_entry(entry_id: int):
    """Get a single history entry by ID."""
    history_manager = HistoryManager()
    entry = history_manager.get_entry(entry_id)

    if not entry:
        raise HTTPException(status_code=404, detail=f"History entry not found: {entry_id}")

    return entry


@router.delete("/history/{entry_id}")
async def delete_history_entry(entry_id: int):
    """Delete a history entry by ID."""
    history_manager = HistoryManager()
    deleted = history_manager.delete_entry(entry_id)

    if not deleted:
        raise HTTPException(status_code=404, detail=f"History entry not found: {entry_id}")

    return {"message": f"History entry {entry_id} deleted"}


@router.delete("/history")
async def clear_history():
    """Clear all history entries."""
    history_manager = HistoryManager()
    count = history_manager.clear_history()
    return {"message": f"Cleared {count} history entries"}


# ============================================================================
# Vocabulary Endpoints
# ============================================================================

@router.get("/vocabulary")
async def get_vocabulary():
    """Get custom vocabulary list."""
    vocab_manager = VocabularyManager()
    vocabulary = vocab_manager.get_vocabulary()
    return {
        "vocabulary": vocabulary,
        "count": len(vocabulary),
    }


@router.put("/vocabulary")
async def update_vocabulary(vocabulary: str = Form(...)):
    """
    Update custom vocabulary (replaces existing).
    Accepts newline-separated list of terms.
    """
    vocab_manager = VocabularyManager()
    success = vocab_manager.set_vocabulary_text(vocabulary)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to save vocabulary")

    new_vocab = vocab_manager.get_vocabulary()
    return {
        "message": "Vocabulary updated",
        "vocabulary": new_vocab,
        "count": len(new_vocab),
    }


@router.post("/vocabulary/add")
async def add_vocabulary_term(term: str = Form(...)):
    """Add a single term to vocabulary."""
    vocab_manager = VocabularyManager()
    success = vocab_manager.add_term(term)

    if not success:
        raise HTTPException(status_code=400, detail="Term already exists or is invalid")

    return {"message": f"Added term: {term}"}


@router.delete("/vocabulary/{term}")
async def remove_vocabulary_term(term: str):
    """Remove a term from vocabulary."""
    vocab_manager = VocabularyManager()
    success = vocab_manager.remove_term(term)

    if not success:
        raise HTTPException(status_code=404, detail=f"Term not found: {term}")

    return {"message": f"Removed term: {term}"}


@router.delete("/vocabulary")
async def clear_vocabulary():
    """Clear all vocabulary."""
    vocab_manager = VocabularyManager()
    vocab_manager.clear_vocabulary()
    return {"message": "Vocabulary cleared"}


# ============================================================================
# Translation Endpoints
# ============================================================================

@router.get("/translate/languages")
async def get_translation_languages():
    """Get available translation languages."""
    try:
        service = TranslationService()
        if not service.is_available():
            return {
                "available": False,
                "languages": [],
                "error": "Translation service not available. Install argostranslate.",
            }

        return {
            "available": True,
            "languages": service.get_available_languages(),
            "installed_packages": service.get_installed_packages(),
        }
    except Exception as e:
        return {
            "available": False,
            "languages": [],
            "error": str(e),
        }


@router.post("/translate")
async def translate_text(
    text: str = Form(...),
    from_language: str = Form(...),
    to_language: str = Form(...),
):
    """
    Translate text from one language to another.
    Uses offline argos-translate models.
    """
    try:
        service = TranslationService()
        if not service.is_available():
            raise HTTPException(
                status_code=503,
                detail="Translation service not available. Install argostranslate.",
            )

        result = service.translate(
            text=text,
            from_code=from_language,
            to_code=to_language,
            auto_install=True,
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Translation failed"),
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Translation error: {str(e)}",
        )


# ============================================================================
# AI Features Endpoints
# ============================================================================

@router.get("/ai/providers")
async def get_ai_providers():
    """Get available AI providers and their status."""
    from ..services.ai_provider import AIProviderFactory, OllamaProvider
    from config.settings import Settings

    settings = Settings()
    ai_config = settings.config.get("ai", {})

    available = AIProviderFactory.get_available_providers(ai_config)
    current_provider = ai_config.get("provider", "ollama")

    # Get Ollama models if available
    ollama_models = []
    if "ollama" in available:
        ollama_models = AIProviderFactory.get_ollama_models()

    return {
        "available_providers": available,
        "current_provider": current_provider if current_provider in available else (available[0] if available else None),
        "providers": {
            "zai": {
                "name": "z.ai",
                "available": "zai" in available,
                "description": "OpenAI-compatible API endpoint",
                "requires": "ZAI_API_KEY",
            },
            "claude": {
                "name": "Claude (Anthropic)",
                "available": "claude" in available,
                "description": "Anthropic Claude API",
                "requires": "ANTHROPIC_API_KEY",
            },
            "ollama": {
                "name": "Ollama (Local)",
                "available": "ollama" in available,
                "description": "Local LLM via Ollama server",
                "requires": "Ollama running at localhost:11434",
                "models": ollama_models,
            },
            "llama": {
                "name": "Llama.cpp (Local)",
                "available": "llama" in available,
                "description": "Local Llama model via llama-cpp-python",
                "requires": "LLAMA_MODEL_PATH",
            },
        },
    }


@router.post("/ai/cleanup")
async def cleanup_transcript(
    transcript: str = Form(...),
    provider: Optional[str] = Form(default=None),
):
    """
    Clean up a transcript using AI.
    Removes filler words, fixes punctuation and grammar.
    """
    from ..services.ai_provider import AIProviderFactory
    from ..services.cleanup_service import CleanupService
    from config.settings import Settings

    settings = Settings()
    ai_config = settings.config.get("ai", {})

    # Determine which provider to use
    available = AIProviderFactory.get_available_providers(ai_config)
    if not available:
        raise HTTPException(
            status_code=503,
            detail="No AI providers available. Configure API keys or local model path.",
        )

    # Use specified provider or fall back to configured default
    provider_type = provider or ai_config.get("provider", "claude")
    if provider_type not in available:
        # Fall back to first available
        provider_type = available[0]

    try:
        # Create provider and service
        provider_config = ai_config.get(provider_type, {})
        ai_provider = AIProviderFactory.create(provider_type, provider_config)
        cleanup_service = CleanupService(ai_provider)

        # Run cleanup
        result = await cleanup_service.cleanup(transcript)
        result["provider_used"] = provider_type

        return result

    except ImportError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Provider {provider_type} dependencies not installed: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Cleanup failed: {str(e)}",
        )


@router.post("/ai/cleanup/diff")
async def cleanup_transcript_with_diff(
    transcript: str = Form(...),
    provider: Optional[str] = Form(default=None),
):
    """
    Clean up a transcript and return a diff-style comparison.
    """
    from ..services.ai_provider import AIProviderFactory
    from ..services.cleanup_service import CleanupService
    from config.settings import Settings

    settings = Settings()
    ai_config = settings.config.get("ai", {})

    # Determine which provider to use
    available = AIProviderFactory.get_available_providers(ai_config)
    if not available:
        raise HTTPException(
            status_code=503,
            detail="No AI providers available. Configure API keys or local model path.",
        )

    provider_type = provider or ai_config.get("provider", "claude")
    if provider_type not in available:
        provider_type = available[0]

    try:
        provider_config = ai_config.get(provider_type, {})
        ai_provider = AIProviderFactory.create(provider_type, provider_config)
        cleanup_service = CleanupService(ai_provider)

        result = await cleanup_service.cleanup_with_diff(transcript)
        result["provider_used"] = provider_type

        return result

    except ImportError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Provider {provider_type} dependencies not installed: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Cleanup failed: {str(e)}",
        )


# ============================================================================
# AI Extraction Endpoints
# ============================================================================

def _get_ai_provider_for_extraction(provider: Optional[str] = None):
    """Helper to get an AI provider for extraction services."""
    from ..services.ai_provider import AIProviderFactory
    from config.settings import Settings

    settings = Settings()
    ai_config = settings.config.get("ai", {})

    available = AIProviderFactory.get_available_providers(ai_config)
    if not available:
        raise HTTPException(
            status_code=503,
            detail="No AI providers available. Configure API keys or local model path.",
        )

    provider_type = provider or ai_config.get("provider", "claude")
    if provider_type not in available:
        provider_type = available[0]

    provider_config = ai_config.get(provider_type, {})
    return AIProviderFactory.create(provider_type, provider_config), provider_type


@router.post("/ai/extract/summary")
async def extract_summary(
    transcript: str = Form(...),
    length: str = Form(default="medium"),
    provider: Optional[str] = Form(default=None),
):
    """
    Generate a summary of the transcript.
    Length options: 'short' (2-3 sentences), 'medium' (1 paragraph), 'long' (2-3 paragraphs)
    """
    from ..services.extraction_service import ExtractionService

    try:
        ai_provider, provider_used = _get_ai_provider_for_extraction(provider)
        service = ExtractionService(ai_provider)
        summary = await service.summarize(transcript, length)

        return {
            "success": True,
            "summary": summary,
            "length": length,
            "provider_used": provider_used,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summary extraction failed: {str(e)}")


@router.post("/ai/extract/key-points")
async def extract_key_points(
    transcript: str = Form(...),
    max_points: int = Form(default=5),
    provider: Optional[str] = Form(default=None),
):
    """
    Extract key points and main topics from the transcript.
    """
    from ..services.extraction_service import ExtractionService

    try:
        ai_provider, provider_used = _get_ai_provider_for_extraction(provider)
        service = ExtractionService(ai_provider)
        key_points = await service.extract_key_points(transcript, max_points)

        return {
            "success": True,
            "key_points": key_points,
            "count": len(key_points),
            "provider_used": provider_used,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Key points extraction failed: {str(e)}")


@router.post("/ai/extract/action-items")
async def extract_action_items(
    transcript: str = Form(...),
    provider: Optional[str] = Form(default=None),
):
    """
    Extract action items, tasks, and commitments from the transcript.
    """
    from ..services.extraction_service import ExtractionService

    try:
        ai_provider, provider_used = _get_ai_provider_for_extraction(provider)
        service = ExtractionService(ai_provider)
        action_items = await service.extract_action_items(transcript)

        return {
            "success": True,
            "action_items": action_items,
            "count": len(action_items),
            "provider_used": provider_used,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Action items extraction failed: {str(e)}")


@router.post("/ai/extract/entities")
async def extract_entities(
    transcript: str = Form(...),
    provider: Optional[str] = Form(default=None),
):
    """
    Extract named entities (people, organizations, locations, dates, products) from the transcript.
    """
    from ..services.extraction_service import ExtractionService

    try:
        ai_provider, provider_used = _get_ai_provider_for_extraction(provider)
        service = ExtractionService(ai_provider)
        entities = await service.extract_entities(transcript)

        return {
            "success": True,
            "entities": entities,
            "provider_used": provider_used,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Entity extraction failed: {str(e)}")


@router.post("/ai/extract/topics")
async def extract_topics(
    transcript: str = Form(...),
    max_topics: int = Form(default=5),
    provider: Optional[str] = Form(default=None),
):
    """
    Extract main topics discussed in the transcript.
    """
    from ..services.extraction_service import ExtractionService

    try:
        ai_provider, provider_used = _get_ai_provider_for_extraction(provider)
        service = ExtractionService(ai_provider)
        topics = await service.extract_topics(transcript, max_topics)

        return {
            "success": True,
            "topics": topics,
            "count": len(topics),
            "provider_used": provider_used,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Topic extraction failed: {str(e)}")


@router.post("/ai/extract/analyze")
async def full_analysis(
    transcript: str = Form(...),
    provider: Optional[str] = Form(default=None),
):
    """
    Run comprehensive analysis on the transcript.
    Returns summary, key points, action items, entities, and topics.
    """
    from ..services.extraction_service import ExtractionService

    try:
        ai_provider, provider_used = _get_ai_provider_for_extraction(provider)
        service = ExtractionService(ai_provider)
        analysis = await service.full_analysis(transcript)

        return {
            "success": True,
            **analysis,
            "provider_used": provider_used,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Full analysis failed: {str(e)}")


@router.post("/ai/extract/meeting-notes")
async def generate_meeting_notes(
    transcript: str = Form(...),
    provider: Optional[str] = Form(default=None),
):
    """
    Generate formatted meeting notes from the transcript.
    Returns notes in Markdown format.
    """
    from ..services.extraction_service import ExtractionService

    try:
        ai_provider, provider_used = _get_ai_provider_for_extraction(provider)
        service = ExtractionService(ai_provider)
        notes = await service.generate_meeting_notes(transcript)

        return {
            "success": True,
            "meeting_notes": notes,
            "format": "markdown",
            "provider_used": provider_used,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Meeting notes generation failed: {str(e)}")


# ============================================================================
# Semantic Search Endpoints
# ============================================================================

@router.get("/semantic-search/status")
async def get_semantic_search_status():
    """Check if semantic search is available and get indexing stats."""
    try:
        from src.web.services.semantic_search import SemanticSearchService
        from src.web.services.embedding_service import is_available

        if not is_available():
            return {
                "available": False,
                "error": "sentence-transformers not installed",
                "indexed_transcripts": 0,
                "total_chunks": 0,
            }

        service = SemanticSearchService()
        return {
            "available": True,
            "indexed_transcripts": service.get_indexed_count(),
            "total_chunks": service.get_total_chunks(),
        }
    except Exception as e:
        return {
            "available": False,
            "error": str(e),
            "indexed_transcripts": 0,
            "total_chunks": 0,
        }


@router.get("/semantic-search")
async def semantic_search(
    q: str = Query(..., description="Search query"),
    limit: int = Query(default=10, ge=1, le=50),
    min_similarity: float = Query(default=0.3, ge=0.0, le=1.0),
):
    """
    Search transcripts by semantic similarity.
    Returns transcripts that are semantically similar to the query,
    even if they don't contain the exact words.
    """
    try:
        from src.web.services.semantic_search import SemanticSearchService
        from src.web.services.embedding_service import is_available

        if not is_available():
            raise HTTPException(
                status_code=503,
                detail="Semantic search not available. Install sentence-transformers."
            )

        service = SemanticSearchService()
        results = service.search(q, limit=limit, min_similarity=min_similarity)

        return {
            "query": q,
            "results": results,
            "count": len(results),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Semantic search failed: {str(e)}")


@router.post("/semantic-search/index/{history_id}")
async def index_transcript(history_id: int):
    """Index a specific transcript for semantic search."""
    try:
        from src.web.services.semantic_search import SemanticSearchService
        from src.web.services.history_manager import HistoryManager
        from src.web.services.embedding_service import is_available

        if not is_available():
            raise HTTPException(
                status_code=503,
                detail="Semantic search not available. Install sentence-transformers."
            )

        # Get the transcript
        manager = HistoryManager()
        entry = manager.get_entry(history_id)
        if not entry:
            raise HTTPException(status_code=404, detail=f"Transcript {history_id} not found")

        transcript_text = entry.get('transcript_text', '')
        if not transcript_text:
            raise HTTPException(status_code=400, detail="Transcript has no text to index")

        # Index it
        service = SemanticSearchService()
        success = service.index_transcript(history_id, transcript_text)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to index transcript")

        return {
            "success": True,
            "message": f"Transcript {history_id} indexed successfully",
            "history_id": history_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indexing failed: {str(e)}")


@router.post("/semantic-search/reindex")
async def reindex_all_transcripts():
    """Reindex all transcripts for semantic search."""
    try:
        from src.web.services.semantic_search import SemanticSearchService
        from src.web.services.embedding_service import is_available

        if not is_available():
            raise HTTPException(
                status_code=503,
                detail="Semantic search not available. Install sentence-transformers."
            )

        service = SemanticSearchService()
        results = service.reindex_all()

        return {
            "success": True,
            "message": "Reindexing complete",
            "indexed": results['success'],
            "failed": results['failed'],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reindexing failed: {str(e)}")


@router.delete("/semantic-search/index/{history_id}")
async def delete_transcript_index(history_id: int):
    """Delete semantic search index for a transcript."""
    try:
        from src.web.services.semantic_search import SemanticSearchService

        service = SemanticSearchService()
        service.delete_index(history_id)

        return {
            "success": True,
            "message": f"Index deleted for transcript {history_id}",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")


# ============================================================================
# Settings Endpoints
# ============================================================================

@router.get("/settings")
async def get_settings():
    """Get current application settings with provider status."""
    from ..services.ai_provider import AIProviderFactory
    from ..services.translation_service import TranslationService
    from config.settings import Settings

    settings = Settings()
    ai_config = settings.config.get("ai", {})

    # Get AI provider availability
    available_providers = AIProviderFactory.get_available_providers(ai_config)

    # Get Ollama models if available
    ollama_models = []
    if "ollama" in available_providers:
        ollama_models = AIProviderFactory.get_ollama_models()

    # Check translation service
    translation_service = TranslationService()
    translation_available = translation_service.is_available()
    translation_error = None
    if not translation_available:
        try:
            import argostranslate
        except ImportError:
            translation_error = "argostranslate not installed. Run: pip install argostranslate"

    return {
        "ai": {
            "provider": ai_config.get("provider", "ollama"),
            "available_providers": available_providers,
            "zai": {
                "configured": bool(ai_config.get("zai", {}).get("api_key")),
                "base_url": ai_config.get("zai", {}).get("base_url", "https://api.z.ai/v1"),
            },
            "claude": {
                "configured": bool(ai_config.get("claude", {}).get("api_key")),
                "model": ai_config.get("claude", {}).get("model", "claude-sonnet-4-20250514"),
            },
            "ollama": {
                "available": "ollama" in available_providers,
                "model": ai_config.get("ollama", {}).get("model", "llama3"),
                "base_url": ai_config.get("ollama", {}).get("base_url", "http://localhost:11434"),
                "models": ollama_models,
            },
            "llama": {
                "configured": bool(ai_config.get("llama", {}).get("model_path")),
                "model_path": ai_config.get("llama", {}).get("model_path"),
            },
        },
        "translation": {
            "available": translation_available,
            "error": translation_error,
        },
        "transcription": settings.config.get("transcription", {}),
        "config_file": settings.config_file_path,
    }


@router.put("/settings/ai")
async def update_ai_settings(
    provider: Optional[str] = Form(default=None),
    zai_api_key: Optional[str] = Form(default=None),
    zai_base_url: Optional[str] = Form(default=None),
    anthropic_api_key: Optional[str] = Form(default=None),
    claude_model: Optional[str] = Form(default=None),
    ollama_model: Optional[str] = Form(default=None),
    ollama_base_url: Optional[str] = Form(default=None),
    llama_model_path: Optional[str] = Form(default=None),
):
    """Update AI provider settings."""
    from config.settings import Settings
    import os

    settings = Settings()

    # Ensure ai section exists
    if "ai" not in settings.config:
        settings.config["ai"] = {}

    ai_config = settings.config["ai"]

    # Update provider
    if provider:
        ai_config["provider"] = provider

    # Update z.ai settings
    if "zai" not in ai_config:
        ai_config["zai"] = {}
    if zai_api_key is not None:
        ai_config["zai"]["api_key"] = zai_api_key if zai_api_key else None
    if zai_base_url:
        ai_config["zai"]["base_url"] = zai_base_url

    # Update Claude settings
    if "claude" not in ai_config:
        ai_config["claude"] = {}
    if anthropic_api_key is not None:
        ai_config["claude"]["api_key"] = anthropic_api_key if anthropic_api_key else None
    if claude_model:
        ai_config["claude"]["model"] = claude_model

    # Update Ollama settings
    if "ollama" not in ai_config:
        ai_config["ollama"] = {}
    if ollama_model:
        ai_config["ollama"]["model"] = ollama_model
    if ollama_base_url:
        ai_config["ollama"]["base_url"] = ollama_base_url

    # Update Llama settings
    if "llama" not in ai_config:
        ai_config["llama"] = {}
    if llama_model_path is not None:
        ai_config["llama"]["model_path"] = llama_model_path if llama_model_path else None

    # Save to config file
    try:
        settings.save_user_config()

        # Also update .env file for environment variable persistence
        _update_env_file({
            "ZAI_API_KEY": ai_config.get("zai", {}).get("api_key"),
            "ZAI_BASE_URL": ai_config.get("zai", {}).get("base_url"),
            "ANTHROPIC_API_KEY": ai_config.get("claude", {}).get("api_key"),
            "CLAUDE_MODEL": ai_config.get("claude", {}).get("model"),
            "OLLAMA_MODEL": ai_config.get("ollama", {}).get("model"),
            "OLLAMA_BASE_URL": ai_config.get("ollama", {}).get("base_url"),
            "LLAMA_MODEL_PATH": ai_config.get("llama", {}).get("model_path"),
            "AI_PROVIDER": ai_config.get("provider"),
        })

        return {
            "success": True,
            "message": "AI settings updated",
            "config_file": settings.config_file_path,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save settings: {str(e)}")


def _update_env_file(env_vars: dict):
    """Helper to update .env file with new values."""
    from pathlib import Path

    env_path = Path.home() / ".transcription" / ".env"
    env_path.parent.mkdir(exist_ok=True)

    # Read existing .env if it exists
    existing = {}
    if env_path.exists():
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    existing[key] = value

    # Update with new values (skip None values, remove empty strings)
    for key, value in env_vars.items():
        if value is None:
            continue
        if value == "":
            existing.pop(key, None)
        else:
            existing[key] = value

    # Write back
    with open(env_path, "w") as f:
        f.write("# Transcription Service Configuration\n")
        f.write("# Generated by the settings UI\n\n")
        for key, value in sorted(existing.items()):
            f.write(f"{key}={value}\n")


@router.get("/settings/ollama/models")
async def get_ollama_models():
    """Get available Ollama models."""
    from ..services.ai_provider import AIProviderFactory, OllamaProvider

    provider = OllamaProvider()
    if not provider.is_available():
        return {
            "available": False,
            "models": [],
            "error": "Ollama not running. Start with: ollama serve",
        }

    models = provider.get_available_models()
    return {
        "available": True,
        "models": models,
        "count": len(models),
    }
