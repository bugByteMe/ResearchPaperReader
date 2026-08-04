from datetime import datetime

from pydantic import BaseModel


class LoginRequest(BaseModel):
    password: str


class CurrentUserOut(BaseModel):
    role: str


class LabelDefinitionBase(BaseModel):
    type: str
    name: str
    description: str = ""


class LabelDefinitionCreate(LabelDefinitionBase):
    pass


class LabelDefinitionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class LabelDefinitionOut(LabelDefinitionBase):
    id: int


    class Config:
        from_attributes = True


class PaperLabelOut(BaseModel):
    id: int
    source: str
    label: LabelDefinitionOut


    class Config:
        from_attributes = True


class PaperOut(BaseModel):
    id: int
    arxiv_id: str
    title: str
    url: str
    pdf_url: str
    abstract: str
    published_date: str
    updated_date: str
    authors: str
    agent_answer: str
    category_answer: str
    tech_route_answer: str
    tech_summary: str
    relevance_answer: str
    trend_answer: str
    quality_answer: str
    is_relevant: bool
    has_new_trend: bool
    is_quality: bool
    last_analyzed_at: datetime | None
    analysis_status: str
    analysis_error: str
    workflow_status: str
    labels: list[PaperLabelOut] = []


    class Config:
        from_attributes = True


class PaperListOut(BaseModel):
    id: int
    title: str
    published_date: str
    authors: str
    last_analyzed_at: datetime | None
    analysis_status: str
    analysis_error: str
    workflow_status: str
    has_new_trend: bool
    is_quality: bool
    created_at: datetime
    labels: list[PaperLabelOut] = []


    class Config:
        from_attributes = True


class PromptOut(BaseModel):
    id: int
    type: str
    content: str
    is_active: bool
    updated_at: datetime


    class Config:
        from_attributes = True


class PromptUpdate(BaseModel):
    content: str


class PaperLabelsUpdate(BaseModel):
    label_ids: list[int]


class MonthlyTrendUpdate(BaseModel):
    title: str
    summary: str


class TrendPaperAdd(BaseModel):
    paper_id: int


class SettingOut(BaseModel):
    key: str
    value: str


    class Config:
        from_attributes = True


class SettingUpdate(BaseModel):
    value: str


class WorkspaceOut(BaseModel):
    id: int
    name: str
    description: str
    analysis_language: str
    arxiv_query: str
    arxiv_categories: str
    arxiv_daily_lookback_days: int
    arxiv_max_results: int
    arxiv_sort_by: str
    arxiv_sort_order: str
    knowledge_base_auto_update_enabled: bool
    is_configured: bool

    class Config:
        from_attributes = True


class WorkspaceUpdate(BaseModel):
    name: str
    description: str = ""
    analysis_language: str = "Chinese"
    arxiv_query: str
    arxiv_categories: str = ""
    arxiv_daily_lookback_days: int = 3
    arxiv_max_results: int = 30
    arxiv_sort_by: str = "submitted_date"
    arxiv_sort_order: str = "descending"
    knowledge_base_auto_update_enabled: bool = False


class SetupLabel(BaseModel):
    type: str
    name: str
    description: str = ""


class SetupRequest(WorkspaceUpdate):
    knowledge_base: str = ""
    labels: list[SetupLabel] = []


class SearchRequest(BaseModel):
    query: str | None = None
    max_results: int | None = None
    categories: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    sort_by: str | None = None
    sort_order: str | None = None


class JobResult(BaseModel):
    imported: int = 0
    analyzed: int = 0
    message: str


class TrendPaperOut(PaperListOut):
    tech_summary: str = ""


class TrendLinkedPaperOut(BaseModel):
    id: int
    title: str
    tech_summary: str = ""


    class Config:
        from_attributes = True


class TrendPaperLinkOut(BaseModel):
    paper: TrendLinkedPaperOut
    contribution_summary: str


    class Config:
        from_attributes = True


class MonthlyTrendOut(BaseModel):
    id: int
    month: str
    title: str
    summary: str
    papers: list[TrendPaperLinkOut]


    class Config:
        from_attributes = True


class MonthlyTrendsOut(BaseModel):
    month: str
    trends: list[MonthlyTrendOut]
    quality_papers: list[TrendPaperOut]
    papers: list[PaperListOut]


class DomainKnowledgeBaseOut(BaseModel):
    id: int
    content: str
    updated_at: datetime


    class Config:
        from_attributes = True


class DomainKnowledgeBaseUpdate(BaseModel):
    content: str


class AnalysisRunOut(BaseModel):
    id: int
    paper_id: int
    status: str
    trigger_type: str
    error_message: str
    started_at: datetime
    finished_at: datetime | None


    class Config:
        from_attributes = True


class DailyRefreshRunOut(BaseModel):
    id: int
    status: str
    trigger_type: str
    matched: int
    imported: int
    skipped_existing: int
    analyzed: int
    date_from: str
    date_to: str
    query: str
    categories: str
    sort_by: str
    sort_order: str
    error_message: str
    started_at: datetime
    finished_at: datetime | None


    class Config:
        from_attributes = True
