"""In-memory job store and runner.

Fine for a single-process dev server. Jobs vanish on restart and aren't shared
between workers; swap `JobStore` for Postgres/Redis (and the runner for a real
queue) before running more than one process.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone

from app.schemas.optimize import JobError, OptimizeJob, OptimizeRequest
from app.services.optimizer import OptimizationError, optimize

logger = logging.getLogger(__name__)

JOB_TTL = timedelta(hours=1)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, OptimizeJob] = {}

    def create(self) -> OptimizeJob:
        self._prune()
        now = _now()
        job = OptimizeJob(
            id=uuid.uuid4().hex,
            status="queued",
            stage="queued",
            progress=0,
            created_at=now,
            updated_at=now,
        )
        self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> OptimizeJob | None:
        return self._jobs.get(job_id)

    def update(self, job_id: str, **fields) -> None:
        job = self._jobs[job_id]
        self._jobs[job_id] = job.model_copy(update={**fields, "updated_at": _now()})

    def _prune(self) -> None:
        cutoff = _now() - JOB_TTL
        for job_id in [j.id for j in self._jobs.values() if j.updated_at < cutoff]:
            del self._jobs[job_id]


store = JobStore()


async def run_job(job_id: str, req: OptimizeRequest) -> None:
    store.update(job_id, status="running", stage="routing", progress=0.05)

    def report(stage: str, progress: float) -> None:
        store.update(job_id, stage=stage, progress=progress)

    try:
        result = await optimize(req, report)
    except OptimizationError as exc:
        store.update(
            job_id,
            status="failed",
            error=JobError(code=exc.code, message=exc.message),
        )
    except Exception:
        logger.exception("Optimization job %s crashed", job_id)
        store.update(
            job_id,
            status="failed",
            error=JobError(code="internal_error", message="Something went wrong."),
        )
    else:
        store.update(job_id, status="succeeded", stage="done", progress=1, result=result)
