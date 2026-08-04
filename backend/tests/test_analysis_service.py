from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import AppSetting, DomainKnowledgeBase, LabelDefinition, Paper, PaperLabel, PaperTrend, PaperTrendLink, Prompt
from app.services import analysis_service


class FakeLLMClient:
    prompts: list[str] = []

    def analyze(self, prompt: str, paper_context: str) -> str:
        self.__class__.prompts.append(prompt)
        if "标签审核" in prompt:
            return '{"labels": [{"id": 1, "matched": true, "reason": "符合"}, {"id": 2, "matched": true, "reason": "符合"}]}'
        if "知识库维护助手" in prompt:
            return '{"content": "## 总览\\n任务：研究机器人导航。\\n研究现状：知识库已根据新论文更新。\\n\\n## 问题类别\\n包含语言指令导航。\\n\\n## 技术路线\\n包含记忆增强导航。\\n\\n## 代表性工作\\n暂无内容。\\n\\n## 近期关注目标\\n2026-06：关注记忆增强导航。", "reason": "沉淀记忆增强导航趋势"}'
        if '"is_relevant"' in prompt:
            return '{"is_relevant": true, "reason": "论文围绕视觉语言导航。"}'
        if '"has_new_trend"' in prompt:
            return '{"has_new_trend": true, "reason": "提出新的导航系统架构。"}'
        if '"is_quality"' in prompt:
            return '{"is_quality": true, "reason": "实验充分且值得重点阅读。"}'
        if '"tech_summary"' in prompt:
            return '{"tech_summary": "论文提出面向导航的视觉语言系统。该系统结合记忆与规划提升导航表现。"}'
        if '"action"' in prompt:
            return '{"action": "create_new_trend", "trend_id": null, "title": "记忆增强导航", "summary": "- 使用记忆增强视觉语言导航", "contribution_summary": "该论文提供了记忆增强导航方案。"}'
        if "分类" in prompt:
            return "类别：Navigation。依据是论文围绕导航任务展开。"
        return "技术路线：Learning-based。方法使用学习式策略。"


class IrrelevantLLMClient:
    def analyze(self, prompt: str, paper_context: str) -> str:
        if '"is_relevant"' in prompt:
            return '{"is_relevant": false, "reason": "论文不是导航主题。"}'
        return "should not be called"


def test_analyze_paper_updates_answers_and_ai_labels(monkeypatch):
    FakeLLMClient.prompts = []
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    db.add_all([
        Prompt(type="category", content="分类", is_active=True),
        Prompt(type="tech_route", content="技术路线", is_active=True),
        Prompt(type="relevance", content="主题筛选", is_active=True),
        Prompt(type="trend", content="趋势", is_active=True),
        Prompt(type="quality", content="优质", is_active=True),
        Prompt(type="tech_summary", content="技术摘要", is_active=True),
        Prompt(type="trend_merge", content="趋势合并", is_active=True),
        Prompt(type="knowledge_update", content="知识库维护助手", is_active=True),
        DomainKnowledgeBase(content="## 总览\n任务：旧知识库。\n研究现状：旧知识库。\n\n## 问题类别\n旧类别。\n\n## 技术路线\n旧路线。\n\n## 代表性工作\n旧工作。\n\n## 近期关注目标\n旧目标。"),
        LabelDefinition(type="category", name="Navigation", description=""),
        LabelDefinition(type="tech_route", name="Learning-based", description=""),
        Paper(
            arxiv_id="2501.00001",
            title="Navigation Paper",
            url="https://arxiv.org/abs/2501.00001",
            pdf_url="https://arxiv.org/pdf/2501.00001",
            abstract="A navigation paper.",
            authors="Test Author",
        ),
    ])
    db.commit()

    paper = db.query(Paper).one()
    monkeypatch.setattr(analysis_service, "fetch_pdf_text", lambda pdf_url: "Full PDF text about navigation.")
    monkeypatch.setattr(analysis_service, "LLMClient", FakeLLMClient)

    updated = analysis_service.analyze_paper(db, paper.id)

    assert "Navigation" in updated.category_answer
    assert "Learning-based" in updated.tech_route_answer
    assert updated.is_relevant is True
    assert "视觉语言系统" in updated.tech_summary
    assert updated.has_new_trend is True
    assert updated.is_quality is True
    assert "导航系统架构" in updated.trend_answer
    assert "重点阅读" in updated.quality_answer
    assert updated.last_analyzed_at is not None
    knowledge_base = db.query(DomainKnowledgeBase).one()
    assert knowledge_base.content == "## 总览\n任务：旧知识库。\n研究现状：旧知识库。\n\n## 问题类别\n旧类别。\n\n## 技术路线\n旧路线。\n\n## 代表性工作\n旧工作。\n\n## 近期关注目标\n旧目标。"
    assert any("旧知识库" in prompt and "分类" in prompt for prompt in FakeLLMClient.prompts)
    assert any("旧知识库" in prompt and "趋势合并" in prompt for prompt in FakeLLMClient.prompts)
    labels = db.query(PaperLabel).filter(PaperLabel.paper_id == paper.id, PaperLabel.source == "ai").all()
    assert len(labels) == 2
    trend = db.query(PaperTrend).one()
    assert trend.month == updated.created_at.strftime("%Y-%m")
    assert trend.title == "记忆增强导航"
    link = db.query(PaperTrendLink).one()
    assert link.paper_id == updated.id
    assert "记忆增强导航方案" in link.contribution_summary


def test_parse_matched_label_ids_from_fenced_json():
    response = """```json
{"labels": [{"id": 1, "matched": true}, {"id": 2, "matched": false}, {"id": 999, "matched": true}]}
```"""

    assert analysis_service.parse_matched_label_ids(response, {1, 2}) == {1}


def test_analyze_paper_skips_knowledge_update_when_disabled(monkeypatch):
    FakeLLMClient.prompts = []
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    original_knowledge = "## 总览\n任务：旧知识库。\n研究现状：旧知识库。\n\n## 问题类别\n旧类别。\n\n## 技术路线\n旧路线。\n\n## 代表性工作\n旧工作。\n\n## 近期关注目标\n旧目标。"
    db.add_all([
        Prompt(type="category", content="分类", is_active=True),
        Prompt(type="tech_route", content="技术路线", is_active=True),
        Prompt(type="relevance", content="主题筛选", is_active=True),
        Prompt(type="trend", content="趋势", is_active=True),
        Prompt(type="quality", content="优质", is_active=True),
        Prompt(type="tech_summary", content="技术摘要", is_active=True),
        Prompt(type="trend_merge", content="趋势合并", is_active=True),
        Prompt(type="knowledge_update", content="知识库维护助手", is_active=True),
        AppSetting(key="knowledge_base_auto_update_enabled", value="false"),
        DomainKnowledgeBase(content=original_knowledge),
        Paper(
            arxiv_id="2501.00004",
            title="Navigation Paper",
            url="https://arxiv.org/abs/2501.00004",
            pdf_url="https://arxiv.org/pdf/2501.00004",
            abstract="A navigation paper.",
            authors="Test Author",
        ),
    ])
    db.commit()

    paper = db.query(Paper).one()
    monkeypatch.setattr(analysis_service, "fetch_pdf_text", lambda pdf_url: "Full PDF text about navigation.")
    monkeypatch.setattr(analysis_service, "LLMClient", FakeLLMClient)

    analysis_service.analyze_paper(db, paper.id)

    assert db.query(DomainKnowledgeBase).one().content == original_knowledge
    assert not any("知识库维护助手" in prompt for prompt in FakeLLMClient.prompts)


def test_analyze_paper_retains_irrelevant_paper_for_audit(monkeypatch):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    db.add_all([
        Prompt(type="relevance", content="主题筛选", is_active=True),
        Paper(
            arxiv_id="2501.00003",
            title="Unrelated Paper",
            url="https://arxiv.org/abs/2501.00003",
            pdf_url="https://arxiv.org/pdf/2501.00003",
            abstract="An unrelated paper.",
            authors="Test Author",
        ),
    ])
    db.commit()

    paper = db.query(Paper).one()
    monkeypatch.setattr(analysis_service, "fetch_pdf_text", lambda pdf_url: "Full PDF text about another topic.")
    monkeypatch.setattr(analysis_service, "LLMClient", IrrelevantLLMClient)

    assert analysis_service.analyze_paper(db, paper.id) is None
    retained = db.query(Paper).one()
    assert retained.workflow_status == "rejected"
    assert retained.is_relevant is False


def test_parse_boolean_judgement_from_fenced_json():
    response = """```json
{"has_new_trend": true, "reason": "新的导航范式"}
```"""

    assert analysis_service.parse_boolean_judgement(response, "has_new_trend") == (True, "新的导航范式")
