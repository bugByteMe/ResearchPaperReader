import json
import logging
import time

from app.config import settings
from app.db import SessionLocal
from app.services.analysis_service import analyze_paper
from app.services.job_service import claim_next_job, complete_job, fail_job, queue_paper_analysis
from app.services.scheduler import run_daily_refresh

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def process_one_job() -> bool:
    db = SessionLocal()
    try:
        job = claim_next_job(db)
        if not job:
            return False
        payload = json.loads(job.payload)
        try:
            if job.kind == "paper_analysis":
                analyze_paper(db, int(payload["paper_id"]), trigger_type=str(payload.get("trigger_type", "worker")), run_id=int(payload["run_id"]))
            elif job.kind == "refresh":
                papers = run_daily_refresh(db, trigger_type=str(payload.get("trigger_type", "scheduled")), refresh_run_id=int(payload["refresh_run_id"]))
                for paper in papers:
                    queue_paper_analysis(db, paper, trigger_type="scheduled")
            else:
                raise ValueError(f"Unsupported job kind: {job.kind}")
            complete_job(db, job)
        except Exception as exc:
            logger.exception("Background job %s failed", job.id)
            fail_job(db, job, exc)
        return True
    finally:
        db.close()


def main() -> None:
    logger.info("AutoPaperReader worker started")
    while True:
        if not process_one_job():
            time.sleep(settings.worker_poll_seconds)


if __name__ == "__main__":
    main()
