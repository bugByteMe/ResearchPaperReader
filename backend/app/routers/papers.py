from datetime import datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, load_only, selectinload

from app.auth import require_admin
from app.config import settings
from app.db import get_db
from app.models import AnalysisRun, LabelDefinition, Paper, PaperLabel, PaperTrend, PaperTrendLink
from app.schemas import MonthlyTrendUpdate, MonthlyTrendsOut, PaperLabelsUpdate, PaperListOut, PaperOut, SearchRequest, TrendPaperAdd
from app.services.arxiv_service import search_and_upsert_papers
from app.services.job_service import queue_paper_analysis
from app.services.workspace_service import require_workspace

router = APIRouter(prefix="/papers", tags=["papers"])


PAPER_LIST_OPTIONS = (
    load_only(
        Paper.id,
        Paper.title,
        Paper.published_date,
        Paper.authors,
        Paper.last_analyzed_at,
        Paper.workflow_status,
        Paper.has_new_trend,
        Paper.is_quality,
        Paper.created_at,
    ),
    selectinload(Paper.labels).selectinload(PaperLabel.label),
)

MONTHLY_PAPER_OPTIONS = (
    load_only(
        Paper.id,
        Paper.title,
        Paper.published_date,
        Paper.authors,
        Paper.last_analyzed_at,
        Paper.workflow_status,
        Paper.has_new_trend,
        Paper.tech_summary,
        Paper.is_quality,
        Paper.created_at,
    ),
    selectinload(Paper.labels).selectinload(PaperLabel.label),
)

def apply_paper_filters(query, label_ids: list[int] | None, year: str | None, title: str | None, abstract: str | None):
    label_ids = label_ids if isinstance(label_ids, list) else []
    if label_ids:
        query = query.join(PaperLabel).filter(PaperLabel.label_id.in_(label_ids)).distinct()
    if year:
        query = query.filter(Paper.published_date.like(f"{year.strip()}%"))
    if title:
        query = query.filter(Paper.title.ilike(f"%{title.strip()}%"))
    if abstract:
        query = query.filter(Paper.abstract.ilike(f"%{abstract.strip()}%"))
    return query


def attach_analysis_state(db: Session, papers: list[Paper]) -> list[Paper]:
    paper_ids = [paper.id for paper in papers]
    if not paper_ids:
        return papers

    latest_runs = db.query(
        AnalysisRun.paper_id,
        func.max(AnalysisRun.started_at).label("started_at"),
    ).filter(AnalysisRun.paper_id.in_(paper_ids)).group_by(AnalysisRun.paper_id).subquery()

    runs = db.query(AnalysisRun).join(
        latest_runs,
        (AnalysisRun.paper_id == latest_runs.c.paper_id) & (AnalysisRun.started_at == latest_runs.c.started_at),
    ).all()
    runs_by_paper_id = {run.paper_id: run for run in runs}

    for paper in papers:
        run = runs_by_paper_id.get(paper.id)
        paper._analysis_status_override = run.status if run else ("succeeded" if paper.last_analyzed_at else "pending")
        paper._analysis_error_override = run.error_message if run else ""
    return papers


def current_month_start() -> datetime:
    today = datetime.utcnow().date()
    return datetime.combine(today.replace(day=1), time.min)


def current_month_key() -> str:
    return current_month_start().strftime("%Y-%m")


def rolling_30_day_start() -> datetime:
    return datetime.utcnow() - timedelta(days=30)


def get_recent_trend(db: Session, trend_id: int) -> PaperTrend:
    trend = db.get(PaperTrend, trend_id)
    if not trend:
        raise HTTPException(status_code=404, detail="Recent trend not found")
    if trend.month == current_month_key():
        return trend
    has_recent_paper = db.query(PaperTrendLink).join(Paper).filter(
        PaperTrendLink.trend_id == trend.id,
        Paper.created_at >= rolling_30_day_start(),
    ).first()
    if not has_recent_paper:
        raise HTTPException(status_code=404, detail="Recent trend not found")
    return trend


@router.get("", response_model=list[PaperListOut])
def list_papers(
    label_ids: list[int] | None = Query(default=None),
    year: str | None = None,
    title: str | None = None,
    abstract: str | None = None,
    db: Session = Depends(get_db),
) -> list[Paper]:
    query = db.query(Paper).options(*PAPER_LIST_OPTIONS).filter(Paper.workflow_status == "accepted", Paper.is_relevant.is_(True))
    query = apply_paper_filters(query, label_ids, year, title, abstract)
    return attach_analysis_state(db, query.order_by(Paper.published_date.desc()).all())


@router.get("/daily", response_model=list[PaperListOut])
def list_daily_papers(
    label_ids: list[int] | None = Query(default=None),
    year: str | None = None,
    title: str | None = None,
    abstract: str | None = None,
    db: Session = Depends(get_db),
) -> list[Paper]:
    start = datetime.combine(datetime.utcnow().date(), time.min)
    query = db.query(Paper).options(*PAPER_LIST_OPTIONS).filter(Paper.workflow_status == "accepted", Paper.is_relevant.is_(True), Paper.created_at >= start)
    query = apply_paper_filters(query, label_ids, year, title, abstract)
    return attach_analysis_state(db, query.order_by(Paper.created_at.desc()).all())


@router.get("/monthly-trends", response_model=MonthlyTrendsOut)
def list_monthly_trends(db: Session = Depends(get_db)) -> dict[str, object]:
    start = rolling_30_day_start()
    window_label = "近30天"
    papers = db.query(Paper).options(*PAPER_LIST_OPTIONS).filter(
        Paper.workflow_status == "accepted",
        Paper.is_relevant.is_(True),
        Paper.created_at >= start,
    ).order_by(Paper.created_at.desc()).all()
    quality_papers = db.query(Paper).options(*MONTHLY_PAPER_OPTIONS).filter(
        Paper.workflow_status == "accepted",
        Paper.is_relevant.is_(True),
        Paper.is_quality.is_(True),
        Paper.created_at >= start,
    ).order_by(Paper.created_at.desc()).all()
    trends = db.query(PaperTrend).options(
        selectinload(PaperTrend.paper_links)
        .selectinload(PaperTrendLink.paper)
        .load_only(
            Paper.id,
            Paper.title,
            Paper.tech_summary,
            Paper.created_at,
            Paper.workflow_status,
            Paper.is_relevant,
        ),
    ).join(PaperTrendLink).join(Paper).filter(
        Paper.created_at >= start,
        Paper.workflow_status == "accepted",
        Paper.is_relevant.is_(True),
    ).distinct().order_by(PaperTrend.updated_at.desc(), PaperTrend.created_at.desc()).all()

    attach_analysis_state(db, papers)
    attach_analysis_state(db, quality_papers)
    for trend in trends:
        trend._paper_links_override = [
            link for link in trend.paper_links
            if link.paper
            and link.paper.created_at >= start
            and link.paper.workflow_status == "accepted"
            and link.paper.is_relevant is True
        ]
    return {"month": window_label, "trends": trends, "quality_papers": quality_papers, "papers": papers}


@router.patch("/monthly-trends/{trend_id}", response_model=MonthlyTrendsOut)
def update_monthly_trend(trend_id: int, payload: MonthlyTrendUpdate, db: Session = Depends(get_db), _admin: str = Depends(require_admin)) -> dict[str, object]:
    trend = get_recent_trend(db, trend_id)
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Trend title cannot be empty")
    trend.title = title
    trend.summary = payload.summary.strip()
    db.commit()
    return list_monthly_trends(db)


@router.post("/monthly-trends/{trend_id}/papers", response_model=MonthlyTrendsOut)
def add_monthly_trend_paper(trend_id: int, payload: TrendPaperAdd, db: Session = Depends(get_db), _admin: str = Depends(require_admin)) -> dict[str, object]:
    trend = get_recent_trend(db, trend_id)
    paper = db.get(Paper, payload.paper_id)
    if not paper or paper.workflow_status != "accepted" or paper.is_relevant is not True:
        raise HTTPException(status_code=404, detail="Accepted relevant paper not found")
    existing = db.query(PaperTrendLink).filter(
        PaperTrendLink.trend_id == trend.id,
        PaperTrendLink.paper_id == paper.id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Paper is already linked to this trend")
    db.add(PaperTrendLink(trend_id=trend.id, paper_id=paper.id))
    db.commit()
    return list_monthly_trends(db)


@router.delete("/monthly-trends/{trend_id}/papers/{paper_id}")
def remove_monthly_trend_paper(trend_id: int, paper_id: int, db: Session = Depends(get_db), _admin: str = Depends(require_admin)) -> dict[str, bool]:
    trend = get_recent_trend(db, trend_id)
    link = db.query(PaperTrendLink).filter(
        PaperTrendLink.trend_id == trend.id,
        PaperTrendLink.paper_id == paper_id,
    ).first()
    if not link:
        raise HTTPException(status_code=404, detail="Trend paper link not found")
    deleted_trend = db.query(PaperTrendLink).filter(PaperTrendLink.trend_id == trend.id).count() <= 1
    if deleted_trend:
        db.delete(trend)
    else:
        db.delete(link)
    db.commit()
    return {"deleted_trend": deleted_trend}


@router.delete("/monthly-trends/{trend_id}")
def delete_monthly_trend(trend_id: int, db: Session = Depends(get_db), _admin: str = Depends(require_admin)) -> dict[str, str]:
    trend = get_recent_trend(db, trend_id)
    db.query(PaperTrendLink).filter(PaperTrendLink.trend_id == trend.id).delete()
    db.delete(trend)
    db.commit()
    return {"message": "deleted"}


@router.get("/today-trends", response_model=MonthlyTrendsOut)
def list_today_trends(db: Session = Depends(get_db)) -> dict[str, object]:
    return list_monthly_trends(db)


@router.post("/search", response_model=list[PaperListOut])
def search_papers(payload: SearchRequest, db: Session = Depends(get_db), _admin: str = Depends(require_admin)) -> list[Paper]:
    workspace = require_workspace(db)
    query = payload.query if payload.query is not None else workspace.arxiv_query
    max_results = payload.max_results if payload.max_results is not None else workspace.arxiv_max_results
    categories = payload.categories if payload.categories is not None else workspace.arxiv_categories
    date_from = payload.date_from if payload.date_from is not None else ""
    date_to = payload.date_to if payload.date_to is not None else ""
    sort_by = payload.sort_by if payload.sort_by is not None else workspace.arxiv_sort_by
    sort_order = payload.sort_order if payload.sort_order is not None else workspace.arxiv_sort_order
    papers = search_and_upsert_papers(db, query, max_results, categories=categories, date_from=date_from, date_to=date_to, sort_by=sort_by, sort_order=sort_order)
    paper_ids = [paper.id for paper in papers]
    for paper in papers:
        paper.workspace_id = workspace.id
        if not paper.last_analyzed_at:
            queue_paper_analysis(db, paper, trigger_type="search")
    if not paper_ids:
        return []
    result = db.query(Paper).options(*PAPER_LIST_OPTIONS).filter(Paper.id.in_(paper_ids), Paper.is_relevant.is_(True)).all()
    return attach_analysis_state(db, result)


@router.get("/{paper_id}", response_model=PaperOut)
def get_paper(paper_id: int, db: Session = Depends(get_db)) -> Paper:
    paper = db.query(Paper).options(selectinload(Paper.labels).selectinload(PaperLabel.label)).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    return attach_analysis_state(db, [paper])[0]


@router.delete("/{paper_id}")
def delete_paper(paper_id: int, db: Session = Depends(get_db), _admin: str = Depends(require_admin)) -> dict[str, str]:
    paper = db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    db.delete(paper)
    db.commit()
    return {"message": "deleted"}


@router.post("/{paper_id}/refresh")
def refresh_paper(paper_id: int, db: Session = Depends(get_db), _admin: str = Depends(require_admin)) -> dict[str, object]:
    paper = db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    job = queue_paper_analysis(db, paper, trigger_type="manual")
    return {"job_id": job.id, "status": job.status}


@router.patch("/{paper_id}/labels", response_model=PaperOut)
def update_paper_labels(paper_id: int, payload: PaperLabelsUpdate, db: Session = Depends(get_db), _admin: str = Depends(require_admin)) -> Paper:
    paper = db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    labels = db.query(LabelDefinition).filter(LabelDefinition.id.in_(payload.label_ids)).all() if payload.label_ids else []
    if len(labels) != len(set(payload.label_ids)):
        raise HTTPException(status_code=400, detail="One or more labels do not exist")

    db.query(PaperLabel).filter(PaperLabel.paper_id == paper_id, PaperLabel.source == "manual").delete()
    for label in labels:
        db.add(PaperLabel(paper_id=paper_id, label_id=label.id, source="manual"))
    db.commit()

    updated = db.query(Paper).options(selectinload(Paper.labels).selectinload(PaperLabel.label)).filter(Paper.id == paper_id).first()
    if not updated:
        raise HTTPException(status_code=404, detail="Paper not found")
    return attach_analysis_state(db, [updated])[0]
