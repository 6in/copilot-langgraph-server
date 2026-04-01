"""Job status polling endpoint (ASYNC-02).

GET /api/job/{job_id} — returns job status from JobStore.
Used by frontend for polling fallback and SSE done-signal result fetch.
"""
from fastapi import APIRouter, Request

from app.api.models import JobStatusResponse

router = APIRouter(prefix="/api", tags=["jobs"])


@router.get("/job/{job_id}", response_model=JobStatusResponse)
async def get_job(job_id: str, request: Request):
    """Return job status. pending if not yet complete, done with result if complete."""
    job_store = request.app.state.job_store
    job = await job_store.get(job_id)
    if not job:
        return JobStatusResponse(status="pending")
    return JobStatusResponse(status=job["status"], result=job.get("result"))
