from datetime import date
from dataclasses import dataclass

import arxiv
from sqlalchemy.orm import Session

from app.models import Paper


SORT_BY = {
    "relevance": arxiv.SortCriterion.Relevance,
    "last_updated_date": arxiv.SortCriterion.LastUpdatedDate,
    "submitted_date": arxiv.SortCriterion.SubmittedDate,
}

SORT_ORDER = {
    "ascending": arxiv.SortOrder.Ascending,
    "descending": arxiv.SortOrder.Descending,
}


@dataclass
class SearchAndUpsertStats:
    papers: list[Paper]
    matched: int
    skipped_existing: int
    query: str


def normalize_arxiv_date(value: str, end_of_day: bool = False) -> str:
    clean = value.strip().replace("-", "")
    if len(clean) == 8 and clean.isdigit():
        return f"{clean}{'2359' if end_of_day else '0000'}"
    if len(clean) == 12 and clean.isdigit():
        return clean
    raise ValueError("arXiv date must be YYYY-MM-DD, YYYYMMDD, or YYYYMMDDHHMM")


def default_today_range() -> tuple[str, str]:
    today = date.today().strftime("%Y%m%d")
    return f"{today}0000", f"{today}2359"


def build_arxiv_query(query: str, categories: str = "", date_from: str = "", date_to: str = "") -> str:
    parts: list[str] = []
    if query:
        parts.append(f"({query})")

    category_terms = [term.strip() for term in categories.split(",") if term.strip()]
    if category_terms:
        parts.append(f"({' OR '.join(f'cat:{term}' for term in category_terms)})")

    if date_from or date_to:
        start = normalize_arxiv_date(date_from or date_to, end_of_day=False)
        end = normalize_arxiv_date(date_to or date_from, end_of_day=True)
    else:
        start, end = default_today_range()
    parts.append(f"submittedDate:[{start} TO {end}]")

    return " AND ".join(parts)


def search_and_upsert_papers(
    db: Session,
    query: str,
    max_results: int,
    categories: str = "",
    date_from: str = "",
    date_to: str = "",
    sort_by: str = "submitted_date",
    sort_order: str = "descending",
) -> list[Paper]:
    return search_and_upsert_papers_with_stats(
        db,
        query,
        max_results,
        categories=categories,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        sort_order=sort_order,
    ).papers


def search_and_upsert_papers_with_stats(
    db: Session,
    query: str,
    max_results: int,
    categories: str = "",
    date_from: str = "",
    date_to: str = "",
    sort_by: str = "submitted_date",
    sort_order: str = "descending",
) -> SearchAndUpsertStats:
    client = arxiv.Client()
    arxiv_query = build_arxiv_query(query, categories, date_from=date_from, date_to=date_to)
    search = arxiv.Search(
        query=arxiv_query,
        max_results=max_results,
        sort_by=SORT_BY.get(sort_by, arxiv.SortCriterion.SubmittedDate),
        sort_order=SORT_ORDER.get(sort_order, arxiv.SortOrder.Descending),
    )
    papers: list[Paper] = []
    matched = 0
    skipped_existing = 0
    for result in client.results(search):
        matched += 1
        arxiv_id = result.entry_id.rsplit("/", 1)[-1]
        paper = db.query(Paper).filter(Paper.arxiv_id == arxiv_id).first()
        if paper:
            skipped_existing += 1
            continue
        paper = Paper(arxiv_id=arxiv_id, title=result.title, url=result.entry_id, pdf_url=result.pdf_url, abstract=result.summary, workflow_status="accepted", is_relevant=False)
        db.add(paper)
        paper.title = result.title
        paper.url = result.entry_id
        paper.pdf_url = result.pdf_url
        paper.abstract = result.summary
        paper.published_date = result.published.isoformat() if result.published else ""
        paper.updated_date = result.updated.isoformat() if result.updated else ""
        paper.authors = ", ".join(author.name for author in result.authors)
        papers.append(paper)
    db.commit()
    for paper in papers:
        db.refresh(paper)
    return SearchAndUpsertStats(papers=papers, matched=matched, skipped_existing=skipped_existing, query=arxiv_query)
