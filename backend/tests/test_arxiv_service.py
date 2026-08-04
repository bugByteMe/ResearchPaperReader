from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Paper
from app.services import arxiv_service
from app.services.arxiv_service import build_arxiv_query, search_and_upsert_papers, search_and_upsert_papers_with_stats


def test_build_arxiv_query_with_categories():
    assert build_arxiv_query("navigation", "cs.RO, cs.AI", date_from="2026-06-11", date_to="2026-06-12") == "(navigation) AND (cat:cs.RO OR cat:cs.AI) AND submittedDate:[202606110000 TO 202606122359]"


def test_build_arxiv_query_without_categories():
    assert build_arxiv_query("navigation", "", date_from="20260611", date_to="20260611") == "(navigation) AND submittedDate:[202606110000 TO 202606112359]"


def test_build_arxiv_query_categories_only():
    assert build_arxiv_query("", "cs.RO", date_from="202606110100", date_to="202606112300") == "(cat:cs.RO) AND submittedDate:[202606110100 TO 202606112300]"


def test_build_arxiv_query_defaults_to_today(monkeypatch):
    class FakeDate:
        @classmethod
        def today(cls):
            from datetime import date
            return date(2026, 6, 11)

    monkeypatch.setattr(arxiv_service, "date", FakeDate)

    assert build_arxiv_query("navigation") == "(navigation) AND submittedDate:[202606110000 TO 202606112359]"


def test_search_and_upsert_papers_skips_existing(monkeypatch):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    db.add(Paper(
        arxiv_id="2501.00001",
        title="Existing Paper",
        url="https://arxiv.org/abs/2501.00001",
        pdf_url="https://arxiv.org/pdf/2501.00001",
        abstract="Existing abstract",
        authors="Existing Author",
    ))
    db.commit()

    results = [
        SimpleNamespace(
            entry_id="https://arxiv.org/abs/2501.00001",
            title="Duplicate Paper",
            pdf_url="https://arxiv.org/pdf/2501.00001",
            summary="Duplicate abstract",
            published=None,
            updated=None,
            authors=[SimpleNamespace(name="Duplicate Author")],
        ),
        SimpleNamespace(
            entry_id="https://arxiv.org/abs/2501.00002",
            title="New Paper",
            pdf_url="https://arxiv.org/pdf/2501.00002",
            summary="New abstract",
            published=None,
            updated=None,
            authors=[SimpleNamespace(name="New Author")],
        ),
    ]

    class FakeClient:
        def results(self, search):
            return results

    monkeypatch.setattr(arxiv_service.arxiv, "Client", FakeClient)

    papers = search_and_upsert_papers(db, "navigation", 10)

    assert [paper.arxiv_id for paper in papers] == ["2501.00002"]
    assert papers[0].workflow_status == "accepted"
    assert db.query(Paper).count() == 2
    assert db.query(Paper).filter(Paper.arxiv_id == "2501.00001").one().title == "Existing Paper"


def test_search_and_upsert_papers_with_stats_counts_matches_and_existing(monkeypatch):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    db.add(Paper(
        arxiv_id="2501.00001",
        title="Existing Paper",
        url="https://arxiv.org/abs/2501.00001",
        pdf_url="https://arxiv.org/pdf/2501.00001",
        abstract="Existing abstract",
        authors="Existing Author",
    ))
    db.commit()

    results = [
        SimpleNamespace(
            entry_id="https://arxiv.org/abs/2501.00001",
            title="Duplicate Paper",
            pdf_url="https://arxiv.org/pdf/2501.00001",
            summary="Duplicate abstract",
            published=None,
            updated=None,
            authors=[SimpleNamespace(name="Duplicate Author")],
        ),
        SimpleNamespace(
            entry_id="https://arxiv.org/abs/2501.00002",
            title="New Paper",
            pdf_url="https://arxiv.org/pdf/2501.00002",
            summary="New abstract",
            published=None,
            updated=None,
            authors=[SimpleNamespace(name="New Author")],
        ),
    ]

    class FakeClient:
        def results(self, search):
            return results

    monkeypatch.setattr(arxiv_service.arxiv, "Client", FakeClient)

    stats = search_and_upsert_papers_with_stats(db, "navigation", 10, date_from="2026-06-11", date_to="2026-06-11")

    assert stats.matched == 2
    assert stats.skipped_existing == 1
    assert [paper.arxiv_id for paper in stats.papers] == ["2501.00002"]
    assert stats.query == "(navigation) AND submittedDate:[202606110000 TO 202606112359]"
