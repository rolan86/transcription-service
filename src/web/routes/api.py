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
