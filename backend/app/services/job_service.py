import json
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import AnalysisRun, BackgroundJob, DailyRefreshRun, Paper


def enqueue_job(
    db: Session, kind: str, payload: dict[str, object], *, workspace_id: int | None = None,
    paper_id: int | None = None, refresh_run_id: int | None = None,
) -> BackgroundJob:
    if paper_id:
        active = db.query(BackgroundJob).filter(
            BackgroundJob.kind == "paper_analysis", BackgroundJob.paper_id == paper_id,
            BackgroundJob.status.in_(("queued", "running")),
        ).first()
        if active:
            return active
    job = BackgroundJob(kind=kind, payload=json.dumps(payload), workspace_id=workspace_id, paper_id=paper_id, refresh_run_id=refresh_run_id)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def queue_paper_analysis(db: Session, paper: Paper, trigger_type: str = "manual") -> BackgroundJob:
    active = db.query(BackgroundJob).filter(
        BackgroundJob.kind == "paper_analysis", BackgroundJob.paper_id == paper.id,
        BackgroundJob.status.in_(("queued", "running")),
    ).first()
    if active:
        return active
    run = AnalysisRun(paper_id=paper.id, trigger_type=trigger_type, status="queued")
    db.add(run)
    db.flush()
    return enqueue_job(db, "paper_analysis", {"paper_id": paper.id, "run_id": run.id, "trigger_type": trigger_type}, paper_id=paper.id, workspace_id=paper.workspace_id)


def queue_refresh(db: Session, trigger_type: str) -> BackgroundJob:
    active = db.query(BackgroundJob).filter(BackgroundJob.kind == "refresh", BackgroundJob.status.in_(("queued", "running"))).first()
    if active:
        return active
    run = DailyRefreshRun(status="queued", trigger_type=trigger_type)
    db.add(run)
    db.flush()
    return enqueue_job(db, "refresh", {"trigger_type": trigger_type, "refresh_run_id": run.id}, refresh_run_id=run.id)


def claim_next_job(db: Session) -> BackgroundJob | None:
    now = datetime.utcnow()
    job = db.query(BackgroundJob).filter(BackgroundJob.status == "queued", BackgroundJob.available_at <= now).order_by(BackgroundJob.created_at).first()
    if not job:
        return None
    job.status = "running"
    job.started_at = now
    job.attempts += 1
    db.commit()
    db.refresh(job)
    return job


def complete_job(db: Session, job: BackgroundJob) -> None:
    job.status = "succeeded"
    job.finished_at = datetime.utcnow()
    job.error_message = ""
    db.commit()


def fail_job(db: Session, job: BackgroundJob, error: Exception) -> None:
    job.error_message = str(error)[:2000]
    if job.attempts < job.max_attempts:
        job.status = "queued"
        job.available_at = datetime.utcnow() + timedelta(seconds=2 ** job.attempts)
        job.started_at = None
    else:
        job.status = "failed"
        job.finished_at = datetime.utcnow()
    db.commit()
