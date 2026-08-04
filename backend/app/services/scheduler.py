from datetime import date, datetime, timedelta

from app.config import settings
from app.models import DailyRefreshRun
from app.services.arxiv_service import search_and_upsert_papers_with_stats
from app.services.workspace_service import require_workspace


def current_day_range(lookback_days: int = 3) -> tuple[str, str]:
    today = date.today().isoformat()
    start = (date.today() - timedelta(days=lookback_days)).isoformat()
    return start, today


def run_daily_refresh(db, trigger_type: str = "scheduled", refresh_run_id: int | None = None):
    run = db.get(DailyRefreshRun, refresh_run_id) if refresh_run_id else DailyRefreshRun(status="queued", trigger_type=trigger_type)
    if run.id is None:
        db.add(run)
        db.flush()
    run.status = "running"
    db.commit()
    try:
        workspace = require_workspace(db)
        query = workspace.arxiv_query
        max_results = workspace.arxiv_max_results
        categories = workspace.arxiv_categories
        lookback_days = workspace.arxiv_daily_lookback_days
        date_from, date_to = current_day_range(lookback_days)
        sort_by = "submitted_date"
        sort_order = "descending"
        result = search_and_upsert_papers_with_stats(db, query, max_results, categories=categories, date_from=date_from, date_to=date_to, sort_by=sort_by, sort_order=sort_order)
        papers = result.papers
        run.status = "succeeded"
        run.matched = result.matched
        run.imported = len(papers)
        run.skipped_existing = result.skipped_existing
        run.analyzed = 0
        run.date_from = date_from
        run.date_to = date_to
        run.query = query
        run.categories = categories
        run.sort_by = sort_by
        run.sort_order = sort_order
        run.finished_at = datetime.utcnow()
        db.commit()
        return papers
    except Exception as exc:
        run.status = "failed"
        run.error_message = str(exc)
        run.finished_at = datetime.utcnow()
        db.commit()
        raise
