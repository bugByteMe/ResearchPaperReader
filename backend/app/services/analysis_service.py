import json
import re
from datetime import datetime

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import AnalysisRun, LabelDefinition, Paper, PaperLabel, PaperTrend, PaperTrendLink, Prompt
from app.services.workspace_service import get_workspace
from app.services.knowledge_base_service import build_knowledge_context, update_knowledge_base_with_ai, with_knowledge_context
from app.services.llm_service import LLMClient, build_paper_context
from app.services.pdf_service import fetch_pdf_text
from app.services.settings_service import get_setting


def get_active_prompt(db: Session, prompt_type: str) -> Prompt:
    prompt = db.query(Prompt).filter(Prompt.type == prompt_type, Prompt.is_active.is_(True)).first()
    if not prompt:
        raise RuntimeError(f"Active prompt not found: {prompt_type}")
    return prompt


def is_knowledge_base_auto_update_enabled(db: Session) -> bool:
    workspace = get_workspace(db)
    return workspace.knowledge_base_auto_update_enabled if workspace else False


def extract_json_object(text: str) -> dict[str, object]:
    cleaned = text.strip()
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
    if fence_match:
        cleaned = fence_match.group(1)
    elif not cleaned.startswith("{"):
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            cleaned = cleaned[start:end + 1]
    parsed = json.loads(cleaned)
    if not isinstance(parsed, dict):
        raise ValueError("Label judgement response must be a JSON object")
    return parsed


def build_boolean_judgement_prompt(prompt: str, result_key: str) -> str:
    return f"""{prompt}

请基于用户提供的论文信息和 PDF 全文片段进行判断。

输出必须是严格 JSON，不要 Markdown，不要解释。格式如下：
{{
  "{result_key}": true,
  "reason": "简短说明判断依据"
}}

要求：
1. "{result_key}" 只能是 true 或 false。
2. reason 必须用中文，简洁说明关键证据。
3. 证据不足时返回 false。"""


def parse_boolean_judgement(response_text: str, result_key: str) -> tuple[bool, str]:
    parsed = extract_json_object(response_text)
    result = parsed.get(result_key)
    if not isinstance(result, bool):
        raise ValueError(f"Judgement JSON must contain boolean {result_key}")
    reason = parsed.get("reason")
    return result, reason if isinstance(reason, str) else ""


def judge_boolean_with_ai(llm: LLMClient, prompt: str, context: str, result_key: str) -> tuple[bool, str]:
    response = llm.analyze(build_boolean_judgement_prompt(prompt, result_key), context)
    return parse_boolean_judgement(response, result_key)


def build_tech_summary_prompt(prompt: str) -> str:
    return f"""{prompt}

请基于用户提供的论文信息和 PDF 全文片段输出严格 JSON，不要 Markdown，不要解释。格式如下：
{{
  "tech_summary": "两句话技术方案总结"
}}

要求：
1. tech_summary 必须是中文。
2. 必须严格控制为两句话。"""


def parse_text_field(response_text: str, field_name: str) -> str:
    parsed = extract_json_object(response_text)
    value = parsed.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Response JSON must contain non-empty {field_name}")
    return value.strip()


def summarize_technical_solution(llm: LLMClient, prompt: str, context: str) -> str:
    response = llm.analyze(build_tech_summary_prompt(prompt), context)
    return parse_text_field(response, "tech_summary")


def paper_month(paper: Paper) -> str:
    value = paper.created_at or datetime.utcnow()
    return value.strftime("%Y-%m")


def build_existing_trends_payload(trends: list[PaperTrend]) -> list[dict[str, object]]:
    payload: list[dict[str, object]] = []
    for trend in trends:
        payload.append({
            "id": trend.id,
            "title": trend.title,
            "summary": trend.summary,
            "papers": [
                {
                    "id": link.paper.id,
                    "title": link.paper.title,
                    "tech_summary": link.paper.tech_summary,
                    "contribution_summary": link.contribution_summary,
                }
                for link in trend.paper_links
                if link.paper is not None
            ],
        })
    return payload


def build_trend_merge_prompt(prompt: str, trends: list[PaperTrend]) -> str:
    return f"""{prompt}

本月已有趋势 JSON：
{json.dumps(build_existing_trends_payload(trends), ensure_ascii=False)}

输出必须是严格 JSON，不要 Markdown，不要解释。格式如下：
{{
  "action": "create_new_trend",
  "trend_id": null,
  "title": "趋势标题",
  "summary": "一到两句话总结",
  "contribution_summary": "该论文对趋势的贡献"
}}

action 只能是 create_new_trend、attach_to_existing_trend、update_existing_trend、no_trend_value。
如果 action 是 attach_to_existing_trend 或 update_existing_trend，trend_id 必须是本月已有趋势 JSON 中的 id。
如果 action 是 no_trend_value，trend_id、title、summary 可以为空字符串或 null。"""


def build_trend_merge_context(paper: Paper) -> str:
    payload = {
        "paper_id": paper.id,
        "title": paper.title,
        "authors": paper.authors,
        "published_date": paper.published_date,
        "tech_summary": paper.tech_summary,
        "category_answer": paper.category_answer,
        "tech_route_answer": paper.tech_route_answer,
    }
    return json.dumps(payload, ensure_ascii=False)


def parse_trend_merge_decision(response_text: str, valid_trend_ids: set[int]) -> dict[str, object]:
    parsed = extract_json_object(response_text)
    action = parsed.get("action")
    if action not in {"create_new_trend", "attach_to_existing_trend", "update_existing_trend", "no_trend_value"}:
        raise ValueError("Trend merge JSON has unsupported action")
    trend_id = parsed.get("trend_id")
    if action in {"attach_to_existing_trend", "update_existing_trend"}:
        if not isinstance(trend_id, int) or trend_id not in valid_trend_ids:
            raise ValueError("Trend merge JSON references an invalid trend_id")
    title = parsed.get("title")
    summary = parsed.get("summary")
    contribution_summary = parsed.get("contribution_summary")
    return {
        "action": action,
        "trend_id": trend_id if isinstance(trend_id, int) else None,
        "title": title.strip() if isinstance(title, str) else "",
        "summary": summary.strip() if isinstance(summary, str) else "",
        "contribution_summary": contribution_summary.strip() if isinstance(contribution_summary, str) else "",
    }


def apply_trend_merge_decision(db: Session, paper: Paper, month: str, decision: dict[str, object]) -> None:
    action = decision["action"]
    if action == "no_trend_value":
        return

    title = str(decision.get("title") or "").strip()
    summary = str(decision.get("summary") or "").strip()
    contribution_summary = str(decision.get("contribution_summary") or "").strip()
    if action == "create_new_trend":
        if not title or not summary:
            raise ValueError("New trend must include title and summary")
        trend = PaperTrend(month=month, title=title, summary=summary)
        db.add(trend)
        db.flush()
    else:
        trend = db.get(PaperTrend, decision.get("trend_id"))
        if not trend or trend.month != month:
            raise ValueError("Trend not found for current month")
        if title:
            trend.title = title
        if summary:
            trend.summary = summary

    link = db.query(PaperTrendLink).filter(PaperTrendLink.trend_id == trend.id, PaperTrendLink.paper_id == paper.id).first()
    if link:
        if contribution_summary:
            link.contribution_summary = contribution_summary
    else:
        db.add(PaperTrendLink(trend_id=trend.id, paper_id=paper.id, contribution_summary=contribution_summary))


def update_monthly_trends_with_ai(db: Session, llm: LLMClient, paper: Paper, knowledge_context: str = "") -> None:
    month = paper_month(paper)
    trends = db.query(PaperTrend).filter(PaperTrend.month == month).order_by(PaperTrend.created_at.asc()).all()
    prompt = with_knowledge_context(get_active_prompt(db, "trend_merge").content, knowledge_context)
    response = llm.analyze(build_trend_merge_prompt(prompt, trends), build_trend_merge_context(paper))
    decision = parse_trend_merge_decision(response, {trend.id for trend in trends})
    apply_trend_merge_decision(db, paper, month, decision)


def build_label_judgement_prompt(labels: list[LabelDefinition], knowledge_context: str = "") -> str:
    label_payload = [
        {"id": label.id, "type": label.type, "name": label.name, "description": label.description}
        for label in labels
    ]
    prompt = f"""你是论文标签审核助手。请只根据用户提供的 Agent Answer，判断每个候选标签是否适用于该论文。

候选标签 JSON：
{json.dumps(label_payload, ensure_ascii=False)}

输出必须是严格 JSON，不要 Markdown，不要解释。格式如下：
{{
  "labels": [
    {{"id": 1, "matched": true, "reason": "简短依据"}},
    {{"id": 2, "matched": false, "reason": "简短依据"}}
  ]
}}

要求：
1. 必须为每个候选标签返回一项。
2. matched 只能是 true 或 false。
3. 如果 Agent Answer 证据不足，matched 应为 false。"""
    return with_knowledge_context(prompt, knowledge_context)


def build_label_judgement_context(paper: Paper) -> str:
    return f"""Title: {paper.title}

Agent Answer:
{paper.agent_answer}"""


def parse_matched_label_ids(response_text: str, valid_label_ids: set[int]) -> set[int]:
    parsed = extract_json_object(response_text)
    items = parsed.get("labels")
    if not isinstance(items, list):
        raise ValueError("Label judgement JSON must contain a labels array")

    matched: set[int] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        label_id = item.get("id")
        is_matched = item.get("matched")
        if isinstance(label_id, int) and label_id in valid_label_ids and is_matched is True:
            matched.add(label_id)
    return matched


def sync_ai_labels(db: Session, paper: Paper, matched_label_ids: set[int]) -> None:
    db.query(PaperLabel).filter(PaperLabel.paper_id == paper.id, PaperLabel.source == "ai").delete()
    existing_manual_ids = {
        row.label_id
        for row in db.query(PaperLabel).filter(PaperLabel.paper_id == paper.id, PaperLabel.source == "manual").all()
    }
    for label_id in matched_label_ids:
        if label_id not in existing_manual_ids:
            db.add(PaperLabel(paper_id=paper.id, label_id=label_id, source="ai"))


def judge_labels_with_ai(db: Session, llm: LLMClient, paper: Paper, knowledge_context: str = "") -> set[int]:
    labels = db.query(LabelDefinition).order_by(LabelDefinition.type, LabelDefinition.name).all()
    if not labels:
        return set()
    response = llm.analyze(build_label_judgement_prompt(labels, knowledge_context), build_label_judgement_context(paper))
    return parse_matched_label_ids(response, {label.id for label in labels})


def latest_analysis_status(paper: Paper) -> str | None:
    if not paper.runs:
        return None
    return max(paper.runs, key=lambda run: run.started_at).status


def queue_analysis_runs(db: Session, papers: list[Paper], trigger_type: str = "search") -> list[tuple[int, int]]:
    queued: list[tuple[int, int]] = []
    for paper in papers:
        if latest_analysis_status(paper) in {"queued", "running"}:
            continue
        run = AnalysisRun(paper_id=paper.id, status="queued", trigger_type=trigger_type)
        db.add(run)
        db.flush()
        queued.append((paper.id, run.id))
    db.commit()
    return queued


def run_queued_analyses(jobs: list[tuple[int, int]]) -> None:
    db = SessionLocal()
    try:
        for paper_id, run_id in jobs:
            try:
                analyze_paper(db, paper_id, trigger_type="search", run_id=run_id)
            except Exception:
                continue
    finally:
        db.close()


def analyze_paper(db: Session, paper_id: int, trigger_type: str = "manual", run_id: int | None = None) -> Paper | None:
    paper = db.get(Paper, paper_id)
    if not paper:
        raise ValueError("Paper not found")

    run = db.get(AnalysisRun, run_id) if run_id else None
    if run is None:
        run = AnalysisRun(paper_id=paper.id, trigger_type=trigger_type)
        db.add(run)
    run.status = "running"
    run.error_message = ""
    db.commit()

    try:
        pdf_text = fetch_pdf_text(paper.pdf_url)
        context = build_paper_context(paper.title, paper.abstract, paper.authors, pdf_text)
        llm = LLMClient()
        workspace = get_workspace(db)
        scope = ""
        if workspace:
            scope = f"\n\n当前工作区：{workspace.name}\n研究范围：{workspace.description or workspace.name}"
        is_relevant, relevance_answer = judge_boolean_with_ai(llm, get_active_prompt(db, "relevance").content + scope, context, "is_relevant")
        paper.is_relevant = is_relevant
        paper.relevance_answer = relevance_answer
        if not is_relevant:
            paper.workflow_status = "rejected"
            run.status = "succeeded"
            run.finished_at = datetime.utcnow()
            db.commit()
            return None

        knowledge_context = build_knowledge_context(db)
        tech_summary = summarize_technical_solution(llm, with_knowledge_context(get_active_prompt(db, "tech_summary").content, knowledge_context), context)
        category_answer = llm.analyze(with_knowledge_context(get_active_prompt(db, "category").content, knowledge_context), context)
        tech_route_answer = llm.analyze(with_knowledge_context(get_active_prompt(db, "tech_route").content, knowledge_context), context)
        has_new_trend, trend_answer = judge_boolean_with_ai(llm, with_knowledge_context(get_active_prompt(db, "trend").content, knowledge_context), context, "has_new_trend")
        is_quality, quality_answer = judge_boolean_with_ai(llm, with_knowledge_context(get_active_prompt(db, "quality").content, knowledge_context), context, "is_quality")

        paper.tech_summary = tech_summary
        paper.category_answer = category_answer
        paper.tech_route_answer = tech_route_answer
        paper.has_new_trend = has_new_trend
        paper.trend_answer = trend_answer
        paper.is_quality = is_quality
        paper.quality_answer = quality_answer
        paper.workflow_status = "accepted"
        paper.agent_answer = (
            f"## 主题筛选\n{relevance_answer}\n\n"
            f"## 技术方案摘要\n{tech_summary}\n\n"
            f"## 类别\n{category_answer}\n\n"
            f"## 技术路线\n{tech_route_answer}\n\n"
            f"## 新技术趋势\n{'是' if has_new_trend else '否'}。{trend_answer}\n\n"
            f"## 优质论文\n{'是' if is_quality else '否'}。{quality_answer}"
        )
        update_monthly_trends_with_ai(db, llm, paper, knowledge_context)
        paper.last_analyzed_at = datetime.utcnow()
        matched_label_ids = judge_labels_with_ai(db, llm, paper, knowledge_context)
        sync_ai_labels(db, paper, matched_label_ids)
        if is_knowledge_base_auto_update_enabled(db):
            update_knowledge_base_with_ai(db, llm, paper)
        run.status = "succeeded"
        run.finished_at = datetime.utcnow()
        db.commit()
        db.refresh(paper)
        return paper
    except Exception as exc:
        db.rollback()
        failed_run = db.get(AnalysisRun, run.id)
        if failed_run:
            failed_run.status = "failed"
            failed_run.error_message = str(exc)[:2000]
            failed_run.finished_at = datetime.utcnow()
            db.commit()
        raise
