from apscheduler.schedulers.blocking import BlockingScheduler

from app.config import settings
from app.db import SessionLocal
from app.services.job_service import queue_refresh


def enqueue_scheduled_refresh() -> None:
    db = SessionLocal()
    try:
        queue_refresh(db, "scheduled")
    finally:
        db.close()


def main() -> None:
    scheduler = BlockingScheduler()
    scheduler.add_job(enqueue_scheduled_refresh, "cron", hour=settings.schedule_hour, id="daily_arxiv_refresh", replace_existing=True, max_instances=1, coalesce=True)
    scheduler.start()


if __name__ == "__main__":
    main()
