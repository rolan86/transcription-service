"""
Job manager for tracking async transcription jobs.
Uses in-memory storage suitable for local deployment.
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum


class JobStatus(str, Enum):
    """Job status enumeration."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Job:
    """Represents a transcription job."""

    job_id: str
    filename: str
    file_path: str
    status: JobStatus = JobStatus.QUEUED
    progress: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    settings: Dict[str, Any] = field(default_factory=dict)


class JobManager:
    """Manages transcription jobs with in-memory storage."""

    _instance: Optional["JobManager"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._jobs: Dict[str, Job] = {}
        self._lock = asyncio.Lock()
        self._expiration_hours = 1  # Jobs expire after 1 hour
        self._initialized = True

    async def create_job(
        self,
        filename: str,
        file_path: str,
        settings: Dict[str, Any],
    ) -> Job:
        """
        Create a new transcription job.

        Args:
            filename: Original filename
            file_path: Path to uploaded file
            settings: Transcription settings

        Returns:
            Created Job object
        """
        job_id = str(uuid.uuid4())[:8]

        job = Job(
            job_id=job_id,
            filename=filename,
            file_path=file_path,
            settings=settings,
        )

        async with self._lock:
            self._jobs[job_id] = job

        # Clean up expired jobs
        await self._cleanup_expired_jobs()

        return job

    async def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID."""
        async with self._lock:
            return self._jobs.get(job_id)

    async def update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        progress: float = 0.0,
        error: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
    ) -> Optional[Job]:
        """
        Update job status.

        Args:
            job_id: Job ID
            status: New status
            progress: Progress (0.0 to 1.0)
            error: Error message if failed
            result: Transcription result if completed

        Returns:
            Updated Job or None if not found
        """
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None

            job.status = status
            job.progress = progress

            if status == JobStatus.PROCESSING and job.started_at is None:
                job.started_at = datetime.now()

            if status in (JobStatus.COMPLETED, JobStatus.FAILED):
                job.completed_at = datetime.now()

            if error:
                job.error = error

            if result:
                job.result = result

            return job

    async def delete_job(self, job_id: str) -> bool:
        """Delete a job by ID."""
        async with self._lock:
            if job_id in self._jobs:
                del self._jobs[job_id]
                return True
            return False

    async def list_jobs(self, limit: int = 50) -> list:
        """List recent jobs."""
        async with self._lock:
            jobs = sorted(
                self._jobs.values(),
                key=lambda j: j.created_at,
                reverse=True,
            )
            return jobs[:limit]

    async def _cleanup_expired_jobs(self) -> None:
        """Remove jobs older than expiration time."""
        expiration_time = datetime.now() - timedelta(hours=self._expiration_hours)

        async with self._lock:
            expired_ids = [
                job_id
                for job_id, job in self._jobs.items()
                if job.created_at < expiration_time
            ]

            for job_id in expired_ids:
                del self._jobs[job_id]


async def run_transcription_job(
    job_id: str,
    transcribe_func: Callable,
    job_manager: JobManager,
) -> None:
    """
    Run a transcription job in the background.

    Args:
        job_id: Job ID
        transcribe_func: Async function to call for transcription
        job_manager: JobManager instance
    """
    from .history_manager import HistoryManager

    job = await job_manager.get_job(job_id)
    if not job:
        return

    try:
        # Mark as processing
        await job_manager.update_job_status(
            job_id=job_id,
            status=JobStatus.PROCESSING,
            progress=0.1,
        )

        # Run transcription
        result = await transcribe_func()

        # Check result
        if result.get("success"):
            await job_manager.update_job_status(
                job_id=job_id,
                status=JobStatus.COMPLETED,
                progress=1.0,
                result=result,
            )

            # Save to history
            try:
                history_manager = HistoryManager()
                history_manager.save_transcription(result, job.filename)
            except Exception as hist_err:
                # Don't fail the job if history save fails
                print(f"Warning: Failed to save to history: {hist_err}")
        else:
            await job_manager.update_job_status(
                job_id=job_id,
                status=JobStatus.FAILED,
                error=result.get("error", "Unknown error"),
            )

    except Exception as e:
        await job_manager.update_job_status(
            job_id=job_id,
            status=JobStatus.FAILED,
            error=str(e),
        )
