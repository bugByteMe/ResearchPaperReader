from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Paper, PaperTrend, PaperTrendLink
from app.routers.papers import add_monthly_trend_paper, current_month_key, delete_monthly_trend, list_monthly_trends, list_papers, remove_monthly_trend_paper, rolling_30_day_start, update_monthly_trend
from app.schemas import MonthlyTrendUpdate, TrendPaperAdd


def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def test_list_papers_filters_by_year_title_and_abstract():
    db = make_session()
    db.add_all([
        Paper(
            arxiv_id="2501.00001",
            title="Visual Navigation With Memory",
            url="https://arxiv.org/abs/2501.00001",
            pdf_url="https://arxiv.org/pdf/2501.00001",
            abstract="A robot navigation method using semantic maps.",
            published_date="2025-01-01T00:00:00Z",
            authors="A. Author",
            workflow_status="accepted",
        ),
        Paper(
            arxiv_id="2401.00001",
            title="Language Grounding",
            url="https://arxiv.org/abs/2401.00001",
            pdf_url="https://arxiv.org/pdf/2401.00001",
            abstract="A robot navigation method using language instructions.",
            published_date="2024-01-01T00:00:00Z",
            authors="B. Author",
            workflow_status="accepted",
        ),
        Paper(
            arxiv_id="2501.00002",
            title="Mapping Benchmark",
            url="https://arxiv.org/abs/2501.00002",
            pdf_url="https://arxiv.org/pdf/2501.00002",
            abstract="A dataset paper without the target phrase.",
            published_date="2025-02-01T00:00:00Z",
            authors="C. Author",
            workflow_status="accepted",
        ),
        Paper(
            arxiv_id="2501.00003",
            title="Visual Navigation Outside Scope",
            url="https://arxiv.org/abs/2501.00003",
            pdf_url="https://arxiv.org/pdf/2501.00003",
            abstract="A robot navigation method using semantic maps.",
            published_date="2025-03-01T00:00:00Z",
            authors="D. Author",
            workflow_status="accepted",
            is_relevant=False,
        ),
    ])
    db.commit()

    papers = list_papers(year="2025", title="navigation", abstract="semantic", db=db)

    assert [paper.title for paper in papers] == ["Visual Navigation With Memory"]


def test_list_monthly_trends_returns_recent_30_day_sections():
    db = make_session()
    recent_start = rolling_30_day_start()
    current_paper = Paper(
        arxiv_id="2606.00001",
        title="Recent Navigation Trend Paper",
        url="https://arxiv.org/abs/2606.00001",
        pdf_url="https://arxiv.org/pdf/2606.00001",
        abstract="A robot navigation paper.",
        published_date="2026-06-01T00:00:00Z",
        authors="A. Author",
        workflow_status="accepted",
        is_relevant=True,
        is_quality=True,
        tech_summary="两句话技术摘要。第二句话。",
        created_at=recent_start + timedelta(days=1),
    )
    old_paper = Paper(
        arxiv_id="2605.00001",
        title="Old Trend Paper",
        url="https://arxiv.org/abs/2605.00001",
        pdf_url="https://arxiv.org/pdf/2605.00001",
        abstract="An older robot navigation paper.",
        published_date="2026-05-01T00:00:00Z",
        authors="B. Author",
        workflow_status="accepted",
        is_relevant=True,
        created_at=recent_start - timedelta(days=1),
    )
    db.add_all([current_paper, old_paper])
    db.flush()
    trend = PaperTrend(month=(recent_start + timedelta(days=1)).strftime("%Y-%m"), title="月度趋势", summary="- 趋势总结", created_at=datetime.utcnow())
    old_trend = PaperTrend(month=(recent_start - timedelta(days=1)).strftime("%Y-%m"), title="旧趋势", summary="- 旧总结", created_at=datetime.utcnow())
    db.add_all([trend, old_trend])
    db.flush()
    db.add_all([
        PaperTrendLink(trend_id=trend.id, paper_id=current_paper.id, contribution_summary="贡献摘要"),
        PaperTrendLink(trend_id=old_trend.id, paper_id=old_paper.id, contribution_summary="旧贡献"),
    ])
    db.commit()

    result = list_monthly_trends(db=db)

    assert result["month"] == "近30天"
    assert [paper.title for paper in result["papers"]] == ["Recent Navigation Trend Paper"]
    assert [paper.title for paper in result["quality_papers"]] == ["Recent Navigation Trend Paper"]
    assert result["trends"][0].title == "月度趋势"
    assert result["trends"][0].paper_links[0].paper.title == "Recent Navigation Trend Paper"


def test_update_monthly_trend_changes_title_and_summary():
    db = make_session()
    trend = PaperTrend(month=current_month_key(), title="旧标题", summary="旧总结")
    db.add(trend)
    db.commit()

    update_monthly_trend(trend.id, MonthlyTrendUpdate(title="  新标题  ", summary="  新总结  "), db=db)

    db.refresh(trend)
    assert trend.title == "新标题"
    assert trend.summary == "新总结"


def test_update_monthly_trend_rejects_non_current_month_trend():
    db = make_session()
    trend = PaperTrend(month="1999-01", title="旧趋势", summary="旧总结")
    db.add(trend)
    db.commit()

    with pytest.raises(HTTPException) as exc:
        update_monthly_trend(trend.id, MonthlyTrendUpdate(title="新标题", summary="新总结"), db=db)

    assert exc.value.status_code == 404


def test_add_monthly_trend_paper_creates_link_without_contribution_summary():
    db = make_session()
    paper = Paper(
        arxiv_id="2606.00002",
        title="Added Trend Paper",
        url="https://arxiv.org/abs/2606.00002",
        pdf_url="https://arxiv.org/pdf/2606.00002",
        abstract="A robot navigation paper.",
        published_date="2026-06-02T00:00:00Z",
        authors="C. Author",
        workflow_status="accepted",
        is_relevant=True,
    )
    trend = PaperTrend(month=current_month_key(), title="月度趋势", summary="趋势总结")
    db.add_all([paper, trend])
    db.commit()

    add_monthly_trend_paper(trend.id, TrendPaperAdd(paper_id=paper.id), db=db)

    link = db.query(PaperTrendLink).one()
    assert link.trend_id == trend.id
    assert link.paper_id == paper.id
    assert link.contribution_summary == ""


def test_add_monthly_trend_paper_rejects_duplicate_link():
    db = make_session()
    paper = Paper(
        arxiv_id="2606.00003",
        title="Duplicate Trend Paper",
        url="https://arxiv.org/abs/2606.00003",
        pdf_url="https://arxiv.org/pdf/2606.00003",
        abstract="A robot navigation paper.",
        published_date="2026-06-03T00:00:00Z",
        authors="D. Author",
        workflow_status="accepted",
        is_relevant=True,
    )
    trend = PaperTrend(month=current_month_key(), title="月度趋势", summary="趋势总结")
    db.add_all([paper, trend])
    db.flush()
    db.add(PaperTrendLink(trend_id=trend.id, paper_id=paper.id))
    db.commit()

    with pytest.raises(HTTPException) as exc:
        add_monthly_trend_paper(trend.id, TrendPaperAdd(paper_id=paper.id), db=db)

    assert exc.value.status_code == 400


def test_remove_monthly_trend_paper_deletes_link_but_keeps_non_empty_trend():
    db = make_session()
    paper_a = Paper(arxiv_id="2606.00004", title="Paper A", url="u", pdf_url="p", abstract="a", authors="A", workflow_status="accepted", is_relevant=True)
    paper_b = Paper(arxiv_id="2606.00005", title="Paper B", url="u", pdf_url="p", abstract="a", authors="B", workflow_status="accepted", is_relevant=True)
    trend = PaperTrend(month=current_month_key(), title="月度趋势", summary="趋势总结")
    db.add_all([paper_a, paper_b, trend])
    db.flush()
    db.add_all([
        PaperTrendLink(trend_id=trend.id, paper_id=paper_a.id),
        PaperTrendLink(trend_id=trend.id, paper_id=paper_b.id),
    ])
    db.commit()

    result = remove_monthly_trend_paper(trend.id, paper_a.id, db=db)

    assert result == {"deleted_trend": False}
    assert db.get(PaperTrend, trend.id) is not None
    assert db.query(PaperTrendLink).filter(PaperTrendLink.trend_id == trend.id).count() == 1


def test_remove_monthly_trend_paper_deletes_empty_trend():
    db = make_session()
    paper = Paper(arxiv_id="2606.00006", title="Last Paper", url="u", pdf_url="p", abstract="a", authors="A", workflow_status="accepted", is_relevant=True)
    trend = PaperTrend(month=current_month_key(), title="月度趋势", summary="趋势总结")
    db.add_all([paper, trend])
    db.flush()
    db.add(PaperTrendLink(trend_id=trend.id, paper_id=paper.id))
    db.commit()

    trend_id = trend.id
    result = remove_monthly_trend_paper(trend_id, paper.id, db=db)

    assert result == {"deleted_trend": True}
    assert db.get(PaperTrend, trend_id) is None


def test_delete_monthly_trend_deletes_links_but_keeps_papers():
    db = make_session()
    paper_a = Paper(arxiv_id="2606.00007", title="Linked Paper A", url="u", pdf_url="p", abstract="a", authors="A", workflow_status="accepted", is_relevant=True)
    paper_b = Paper(arxiv_id="2606.00008", title="Linked Paper B", url="u", pdf_url="p", abstract="a", authors="B", workflow_status="accepted", is_relevant=True)
    trend = PaperTrend(month=current_month_key(), title="待删除趋势", summary="趋势总结")
    db.add_all([paper_a, paper_b, trend])
    db.flush()
    db.add_all([
        PaperTrendLink(trend_id=trend.id, paper_id=paper_a.id),
        PaperTrendLink(trend_id=trend.id, paper_id=paper_b.id),
    ])
    db.commit()
    trend_id = trend.id
    paper_ids = [paper_a.id, paper_b.id]

    result = delete_monthly_trend(trend_id, db=db)

    assert result == {"message": "deleted"}
    assert db.get(PaperTrend, trend_id) is None
    assert db.query(PaperTrendLink).count() == 0
    assert [db.get(Paper, paper_id).title for paper_id in paper_ids] == ["Linked Paper A", "Linked Paper B"]
