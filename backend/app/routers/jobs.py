from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import require_admin
from app.db import get_db
from app.models import AnalysisRun, BackgroundJob, DailyRefreshRun
from app.schemas import AnalysisRunOut, DailyRefreshRunOut, JobResult
from app.services.job_service import queue_refresh

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/run-scheduled-refresh", response_model=JobResult)
def run_scheduled_refresh(
    db: Session = Depends(get_db), _admin: str = Depends(require_admin)
) -> JobResult:
    job = queue_refresh(db, "manual")
    return JobResult(imported=0, analyzed=0, message=f"refresh queued (job {job.id})")


@router.get("/analysis-runs", response_model=list[AnalysisRunOut])
def list_analysis_runs(db: Session = Depends(get_db), _admin: str = Depends(require_admin)) -> list[AnalysisRun]:
    return db.query(AnalysisRun).order_by(AnalysisRun.started_at.desc()).limit(100).all()


@router.get("/daily-refresh-runs", response_model=list[DailyRefreshRunOut])
def list_daily_refresh_runs(db: Session = Depends(get_db), _admin: str = Depends(require_admin)) -> list[DailyRefreshRun]:
    return db.query(DailyRefreshRun).order_by(DailyRefreshRun.started_at.desc()).limit(100).all()


@router.get("", response_model=list[dict[str, object]])
def list_jobs(db: Session = Depends(get_db), _admin: str = Depends(require_admin)):
    return [
        {"id": job.id, "kind": job.kind, "status": job.status, "error_message": job.error_message, "created_at": job.created_at, "started_at": job.started_at, "finished_at": job.finished_at}
        for job in db.query(BackgroundJob).order_by(BackgroundJob.created_at.desc()).limit(100).all()
    ]
