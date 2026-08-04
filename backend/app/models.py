from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Paper(Base, TimestampMixin):
    __tablename__ = "papers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    arxiv_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(512))
    url: Mapped[str] = mapped_column(String(1024))
    pdf_url: Mapped[str] = mapped_column(String(1024))
    abstract: Mapped[str] = mapped_column(Text)
    published_date: Mapped[str] = mapped_column(String(64), default="")
    updated_date: Mapped[str] = mapped_column(String(64), default="")
    authors: Mapped[str] = mapped_column(Text, default="")
    agent_answer: Mapped[str] = mapped_column(Text, default="")
    category_answer: Mapped[str] = mapped_column(Text, default="")
    tech_route_answer: Mapped[str] = mapped_column(Text, default="")
    tech_summary: Mapped[str] = mapped_column(Text, default="")
    relevance_answer: Mapped[str] = mapped_column(Text, default="")
    trend_answer: Mapped[str] = mapped_column(Text, default="")
    quality_answer: Mapped[str] = mapped_column(Text, default="")
    is_relevant: Mapped[bool] = mapped_column(Boolean, default=True)
    has_new_trend: Mapped[bool] = mapped_column(Boolean, default=False)
    is_quality: Mapped[bool] = mapped_column(Boolean, default=False)
    last_analyzed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    workflow_status: Mapped[str] = mapped_column(String(32), default="accepted")
    workspace_id: Mapped[int | None] = mapped_column(ForeignKey("workspaces.id"), nullable=True, index=True)

    labels: Mapped[list["PaperLabel"]] = relationship(back_populates="paper", cascade="all, delete-orphan")
    runs: Mapped[list["AnalysisRun"]] = relationship(back_populates="paper", cascade="all, delete-orphan")
    trend_links: Mapped[list["PaperTrendLink"]] = relationship(back_populates="paper", cascade="all, delete-orphan")

    @property
    def analysis_status(self) -> str:
        override = getattr(self, "_analysis_status_override", None)
        if override is not None:
            return override
        if not self.runs:
            return "succeeded" if self.last_analyzed_at else "pending"
        latest = max(self.runs, key=lambda run: run.started_at)
        return latest.status

    @property
    def analysis_error(self) -> str:
        override = getattr(self, "_analysis_error_override", None)
        if override is not None:
            return override
        if not self.runs:
            return ""
        latest = max(self.runs, key=lambda run: run.started_at)
        return latest.error_message


class Prompt(Base, TimestampMixin):
    __tablename__ = "prompts"
    __table_args__ = (UniqueConstraint("type", "is_active", name="uq_active_prompt_type"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[str] = mapped_column(String(32), index=True)
    content: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    workspace_id: Mapped[int | None] = mapped_column(ForeignKey("workspaces.id"), nullable=True, index=True)


class LabelDefinition(Base, TimestampMixin):
    __tablename__ = "label_definitions"
    __table_args__ = (UniqueConstraint("type", "name", name="uq_label_type_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text, default="")
    workspace_id: Mapped[int | None] = mapped_column(ForeignKey("workspaces.id"), nullable=True, index=True)

    paper_labels: Mapped[list["PaperLabel"]] = relationship(back_populates="label")


class PaperLabel(Base, TimestampMixin):
    __tablename__ = "paper_labels"
    __table_args__ = (UniqueConstraint("paper_id", "label_id", name="uq_paper_label"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    paper_id: Mapped[int] = mapped_column(ForeignKey("papers.id"), index=True)
    label_id: Mapped[int] = mapped_column(ForeignKey("label_definitions.id"), index=True)
    source: Mapped[str] = mapped_column(String(32), default="manual")

    paper: Mapped[Paper] = relationship(back_populates="labels")
    label: Mapped[LabelDefinition] = relationship(back_populates="paper_labels")


class PaperTrend(Base, TimestampMixin):
    __tablename__ = "paper_trends"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    month: Mapped[str] = mapped_column(String(7), index=True)
    title: Mapped[str] = mapped_column(String(256))
    summary: Mapped[str] = mapped_column(Text, default="")

    paper_links: Mapped[list["PaperTrendLink"]] = relationship(back_populates="trend", cascade="all, delete-orphan")

    @property
    def papers(self) -> list["PaperTrendLink"]:
        override = getattr(self, "_paper_links_override", None)
        if override is not None:
            return override
        return self.paper_links


class PaperTrendLink(Base, TimestampMixin):
    __tablename__ = "paper_trend_links"
    __table_args__ = (UniqueConstraint("trend_id", "paper_id", name="uq_paper_trend_link"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trend_id: Mapped[int] = mapped_column(ForeignKey("paper_trends.id"), index=True)
    paper_id: Mapped[int] = mapped_column(ForeignKey("papers.id"), index=True)
    contribution_summary: Mapped[str] = mapped_column(Text, default="")

    trend: Mapped[PaperTrend] = relationship(back_populates="paper_links")
    paper: Mapped[Paper] = relationship(back_populates="trend_links")


class DomainKnowledgeBase(Base, TimestampMixin):
    __tablename__ = "domain_knowledge_base"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    content: Mapped[str] = mapped_column(Text, default="")
    workspace_id: Mapped[int | None] = mapped_column(ForeignKey("workspaces.id"), nullable=True, index=True)


class DailyRefreshRun(Base):
    __tablename__ = "daily_refresh_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(32), default="running")
    trigger_type: Mapped[str] = mapped_column(String(32), default="scheduled")
    matched: Mapped[int] = mapped_column(Integer, default=0)
    imported: Mapped[int] = mapped_column(Integer, default=0)
    skipped_existing: Mapped[int] = mapped_column(Integer, default=0)
    analyzed: Mapped[int] = mapped_column(Integer, default=0)
    date_from: Mapped[str] = mapped_column(String(16), default="")
    date_to: Mapped[str] = mapped_column(String(16), default="")
    query: Mapped[str] = mapped_column(Text, default="")
    categories: Mapped[str] = mapped_column(Text, default="")
    sort_by: Mapped[str] = mapped_column(String(32), default="")
    sort_order: Mapped[str] = mapped_column(String(32), default="")
    error_message: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    workspace_id: Mapped[int | None] = mapped_column(ForeignKey("workspaces.id"), nullable=True, index=True)


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    paper_id: Mapped[int] = mapped_column(ForeignKey("papers.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="running")
    trigger_type: Mapped[str] = mapped_column(String(32), default="manual")
    error_message: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    paper: Mapped[Paper] = relationship(back_populates="runs")


class Workspace(Base, TimestampMixin):
    __tablename__ = "workspaces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    analysis_language: Mapped[str] = mapped_column(String(32), default="Chinese")
    arxiv_query: Mapped[str] = mapped_column(Text)
    arxiv_categories: Mapped[str] = mapped_column(Text, default="")
    arxiv_daily_lookback_days: Mapped[int] = mapped_column(Integer, default=3)
    arxiv_max_results: Mapped[int] = mapped_column(Integer, default=30)
    arxiv_sort_by: Mapped[str] = mapped_column(String(32), default="submitted_date")
    arxiv_sort_order: Mapped[str] = mapped_column(String(32), default="descending")
    knowledge_base_auto_update_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    is_configured: Mapped[bool] = mapped_column(Boolean, default=False)


class BackgroundJob(Base, TimestampMixin):
    __tablename__ = "background_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    payload: Mapped[str] = mapped_column(Text, default="{}")
    error_message: Mapped[str] = mapped_column(Text, default="")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    available_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    workspace_id: Mapped[int | None] = mapped_column(ForeignKey("workspaces.id"), nullable=True, index=True)
    paper_id: Mapped[int | None] = mapped_column(ForeignKey("papers.id"), nullable=True, index=True)
    refresh_run_id: Mapped[int | None] = mapped_column(ForeignKey("daily_refresh_runs.id"), nullable=True, index=True)


class AppSetting(Base, TimestampMixin):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    value: Mapped[str] = mapped_column(Text)
