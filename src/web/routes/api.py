"""
REST API endpoints for batch transcription.
"""

import asyncio
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
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
                # Transcribe
                result = await api.transcribe_file(
                    file_path=temp_path,
                    **settings,
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
