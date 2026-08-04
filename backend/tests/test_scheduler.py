from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import DailyRefreshRun, Workspace
from app.services import scheduler
from app.services.arxiv_service import SearchAndUpsertStats


def make_workspace(db):
    workspace = Workspace(
        name="Test field", description="Test research", arxiv_query="test query", arxiv_categories="cs.AI",
        arxiv_daily_lookback_days=3, arxiv_max_results=10, arxiv_sort_by="relevance", arxiv_sort_order="ascending", is_configured=True,
    )
    db.add(workspace)
    db.commit()
    return workspace


def test_run_daily_refresh_uses_workspace_window_and_records_diagnostics(monkeypatch):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    make_workspace(db)
    captured = {}

    class FakeDate:
        @classmethod
        def today(cls):
            return date(2026, 6, 11)

    def fake_search(db, query, max_results, categories="", date_from="", date_to="", sort_by="", sort_order=""):
        captured.update(query=query, max_results=max_results, categories=categories, date_from=date_from, date_to=date_to, sort_by=sort_by, sort_order=sort_order)
        return SearchAndUpsertStats(papers=[], matched=4, skipped_existing=4, query="built query")

    monkeypatch.setattr(scheduler, "date", FakeDate)
    monkeypatch.setattr(scheduler, "search_and_upsert_papers_with_stats", fake_search)
    assert scheduler.run_daily_refresh(db) == []
    assert captured == {"query": "test query", "max_results": 10, "categories": "cs.AI", "date_from": "2026-06-08", "date_to": "2026-06-11", "sort_by": "submitted_date", "sort_order": "descending"}
    run = db.query(DailyRefreshRun).one()
    assert run.status == "succeeded"
    assert run.matched == 4
    assert run.skipped_existing == 4


def test_run_daily_refresh_records_failure(monkeypatch):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    make_workspace(db)
    monkeypatch.setattr(scheduler, "search_and_upsert_papers_with_stats", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("search failed")))
    try:
        scheduler.run_daily_refresh(db, trigger_type="manual")
    except RuntimeError:
        pass
    run = db.query(DailyRefreshRun).one()
    assert run.status == "failed"
    assert "search failed" in run.error_message
