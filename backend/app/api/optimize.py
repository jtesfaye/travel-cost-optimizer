from fastapi import APIRouter, BackgroundTasks, HTTPException, Response

from app.core.config import settings
from app.schemas.optimize import OptimizeJob, OptimizeRequest
from app.services.jobs import run_job, store

router = APIRouter(prefix="/optimizations", tags=["optimizations"])


@router.post("", response_model=OptimizeJob, status_code=202)
async def start_optimization(
    req: OptimizeRequest, background: BackgroundTasks, response: Response
):
    job = store.create()
    background.add_task(run_job, job.id, req)
    response.headers["Location"] = (
        f"{settings.api_v1_prefix}/optimizations/{job.id}"
    )
    return job


@router.get("/{job_id}", response_model=OptimizeJob)
async def get_optimization(job_id: str):
    job = store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Optimization job not found")
    return job
