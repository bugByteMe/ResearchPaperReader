import json
import re

from sqlalchemy.orm import Session

from app.models import DomainKnowledgeBase, Paper, Prompt
from app.services.llm_service import LLMClient


DEFAULT_KNOWLEDGE_BASE_CONTENT = """## 领域总览

记录当前工作区的研究范围、核心问题和术语。

## 问题类别

记录可复用的问题分类。

## 技术路线

记录方法范式、假设和关键组件。

## 代表性工作

记录具有长期参考价值的论文。

## 近期关注目标

记录需要持续跟踪的开放问题和趋势。"""


def get_or_create_knowledge_base(db: Session) -> DomainKnowledgeBase:
    knowledge_base = db.query(DomainKnowledgeBase).order_by(DomainKnowledgeBase.id.asc()).first()
    if knowledge_base:
        return knowledge_base
    knowledge_base = DomainKnowledgeBase(content=DEFAULT_KNOWLEDGE_BASE_CONTENT)
    db.add(knowledge_base)
    db.commit()
    db.refresh(knowledge_base)
    return knowledge_base


def build_knowledge_context(db: Session) -> str:
    return get_or_create_knowledge_base(db).content.strip()


def with_knowledge_context(prompt: str, knowledge_context: str) -> str:
    if not knowledge_context.strip():
        return prompt
    return f"""{prompt}

以下是当前工作区的领域知识库，供分析时参考。请不要机械复述知识库，只在有助于判断类别、技术路线、质量或趋势时使用：

{knowledge_context}"""


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
        raise ValueError("Knowledge update response must be a JSON object")
    return parsed


def build_knowledge_update_prompt(prompt: str, current_knowledge: str) -> str:
    return f"""{prompt}

当前知识库：
{current_knowledge}

输出必须是严格 JSON，不要 Markdown 代码块，不要额外解释。格式如下：
{{
  "content": "更新后的完整知识库 Markdown",
  "reason": "简短说明本次更新依据"
}}

要求：
1. content 必须是完整知识库全文，不能只返回新增内容。
2. content 必须包含：总览、问题类别、技术路线、代表性工作、近期关注目标。
3. 如果新论文没有可沉淀的通用知识，也应返回原知识库全文。"""


def build_knowledge_update_context(paper: Paper) -> str:
    payload = {
        "title": paper.title,
        "authors": paper.authors,
        "published_date": paper.published_date,
        "agent_answer": paper.agent_answer,
        "tech_summary": paper.tech_summary,
        "category_answer": paper.category_answer,
        "tech_route_answer": paper.tech_route_answer,
        "trend_answer": paper.trend_answer,
        "quality_answer": paper.quality_answer,
        "is_quality": paper.is_quality,
        "has_new_trend": paper.has_new_trend,
    }
    return json.dumps(payload, ensure_ascii=False)


def parse_knowledge_update(response_text: str) -> str:
    parsed = extract_json_object(response_text)
    content = parsed.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Knowledge update JSON must contain non-empty content")
    return content.strip()


def update_knowledge_base_with_ai(db: Session, llm: LLMClient, paper: Paper) -> DomainKnowledgeBase:
    knowledge_base = get_or_create_knowledge_base(db)
    prompt = db.query(Prompt).filter(Prompt.type == "knowledge_update", Prompt.is_active.is_(True)).first()
    if not prompt:
        raise RuntimeError("Active prompt not found: knowledge_update")
    response = llm.analyze(build_knowledge_update_prompt(prompt.content, knowledge_base.content), build_knowledge_update_context(paper))
    knowledge_base.content = parse_knowledge_update(response)
    db.flush()
    return knowledge_base
