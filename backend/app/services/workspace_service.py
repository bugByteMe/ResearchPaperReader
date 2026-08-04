from sqlalchemy.orm import Session

from app.models import DomainKnowledgeBase, LabelDefinition, Prompt, Workspace
from app.seed import PROMPT_TYPES


VALID_SORT_FIELDS = {"submitted_date", "last_updated_date", "relevance"}
VALID_SORT_ORDERS = {"ascending", "descending"}


def get_workspace(db: Session) -> Workspace | None:
    return db.query(Workspace).order_by(Workspace.id).first()


def require_workspace(db: Session) -> Workspace:
    workspace = get_workspace(db)
    if not workspace or not workspace.is_configured:
        raise RuntimeError("Workspace setup is incomplete")
    return workspace


def validate_workspace_values(
    name: str,
    query: str,
    max_results: int,
    lookback_days: int,
    sort_by: str,
    sort_order: str,
) -> None:
    if not name.strip() or len(name.strip()) > 128:
        raise ValueError("Workspace name must contain 1 to 128 characters")
    if not query.strip() or len(query) > 2000:
        raise ValueError("arXiv query must contain 1 to 2000 characters")
    if not 1 <= max_results <= 100:
        raise ValueError("Maximum results must be between 1 and 100")
    if not 1 <= lookback_days <= 30:
        raise ValueError("Lookback days must be between 1 and 30")
    if sort_by not in VALID_SORT_FIELDS:
        raise ValueError("Unsupported arXiv sort field")
    if sort_order not in VALID_SORT_ORDERS:
        raise ValueError("Unsupported arXiv sort order")


def create_workspace(
    db: Session,
    *,
    name: str,
    description: str,
    analysis_language: str,
    arxiv_query: str,
    arxiv_categories: str,
    arxiv_daily_lookback_days: int,
    arxiv_max_results: int,
    arxiv_sort_by: str,
    arxiv_sort_order: str,
    knowledge_base: str,
    labels: list[tuple[str, str, str]],
) -> Workspace:
    if get_workspace(db):
        raise ValueError("A local workspace is already configured")
    validate_workspace_values(name, arxiv_query, arxiv_max_results, arxiv_daily_lookback_days, arxiv_sort_by, arxiv_sort_order)
    workspace = Workspace(
        name=name.strip(), description=description.strip(), analysis_language=analysis_language.strip() or "Chinese",
        arxiv_query=arxiv_query.strip(), arxiv_categories=arxiv_categories.strip(),
        arxiv_daily_lookback_days=arxiv_daily_lookback_days, arxiv_max_results=arxiv_max_results,
        arxiv_sort_by=arxiv_sort_by, arxiv_sort_order=arxiv_sort_order, is_configured=True,
    )
    db.add(workspace)
    db.flush()
    for prompt_type, content in PROMPT_TYPES.items():
        db.add(Prompt(type=prompt_type, content=content, is_active=True, workspace_id=workspace.id))
    db.add(DomainKnowledgeBase(content=knowledge_base.strip(), workspace_id=workspace.id))
    for label_type, label_name, label_description in labels:
        if label_type not in {"category", "tech_route"} or not label_name.strip():
            continue
        db.add(LabelDefinition(type=label_type, name=label_name.strip(), description=label_description.strip(), workspace_id=workspace.id))
    db.commit()
    db.refresh(workspace)
    return workspace


def update_workspace(db: Session, workspace: Workspace, **values: object) -> Workspace:
    next_values = {
        "name": str(values.get("name", workspace.name)),
        "query": str(values.get("arxiv_query", workspace.arxiv_query)),
        "max_results": int(values.get("arxiv_max_results", workspace.arxiv_max_results)),
        "lookback_days": int(values.get("arxiv_daily_lookback_days", workspace.arxiv_daily_lookback_days)),
        "sort_by": str(values.get("arxiv_sort_by", workspace.arxiv_sort_by)),
        "sort_order": str(values.get("arxiv_sort_order", workspace.arxiv_sort_order)),
    }
    validate_workspace_values(**next_values)
    for key, value in values.items():
        if hasattr(workspace, key):
            setattr(workspace, key, value)
    db.commit()
    db.refresh(workspace)
    return workspace
