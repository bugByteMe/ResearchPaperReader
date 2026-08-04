from sqlalchemy.orm import Session

from app.models import AppSetting, LabelDefinition, Prompt


DEFAULT_CATEGORY_PROMPT = """根据工作区的研究范围，为论文归纳适合该领域的研究类别，并给出简洁依据。"""

DEFAULT_TECH_ROUTE_PROMPT = """根据工作区知识库判断论文采用的技术路线；如果不属于已有路线，请明确说明。"""

DEFAULT_RELEVANCE_PROMPT = """判断论文是否属于当前工作区定义的研究范围。工作区名称和描述是唯一的领域边界；不要根据其他领域的惯例推断相关性。"""

DEFAULT_TREND_PROMPT = """根据知识库中的技术路线，判断这篇论文是否体现了值得关注的新技术趋势。要非常严格，如果只是任务设定上不同，或者技术细节上有点小改动，就不要算作新技术。"""

DEFAULT_QUALITY_PROMPT = """判断这篇论文是否是优质论文。

根据知识库判断论文是否有提出现有技术路线以外的新技术。要非常严格，如果只是在现有技术路线上做改进，就不算是新技术。
只有提出突破性技术创新的论文才算优质论文。"""

DEFAULT_TECH_SUMMARY_PROMPT = """根据知识库，请用两句话总结这篇论文：第一句话说明核心问题与技术范式，第二句话说明关键技术组件或实验贡献。表述精简。"""

DEFAULT_TREND_MERGE_PROMPT = """你是研究论文趋势归纳助手，根据工作区知识库以及分析过的近期技术趋势，判断新论文技术方案是否需要创建新趋势、绑定到已有趋势，或更新已有趋势描述。

要非常严格，如果只是任务设定上不同，或者技术细节上有点小改动，就不要算作新技术。
尽量把新论文归到已有技术趋势中，并在必要时更新该趋势总结。
只有当论文技术有非常大的不同时，才设定为新技术趋势。

趋势总结必须以一到两句话的形式呈现，需要精简，不能过于关注细节改进。"""

DEFAULT_KNOWLEDGE_UPDATE_PROMPT = """你是研究领域知识库维护助手。请根据当前知识库和新论文分析结果，更新领域知识库全文。

知识库必须保持以下结构：
1. 总览：参考已有的写作结构，精准简洁地进行更新。
2. 问题类别：参考已有的写作结构，并相应地增加新问题类别。
3. 技术路线：参考已有的写作结构，并相应地增加新技术类别。

要求：
1. 输出更新后的完整知识库，而不是增量 patch。
2. 不要因为单篇论文过度改写稳定结论；只沉淀可复用的领域知识、趋势和关系。
3. 使用中文，保留 Markdown 标题。"""

PROMPT_TYPES = {
    "category": DEFAULT_CATEGORY_PROMPT,
    "tech_route": DEFAULT_TECH_ROUTE_PROMPT,
    "relevance": DEFAULT_RELEVANCE_PROMPT,
    "trend": DEFAULT_TREND_PROMPT,
    "quality": DEFAULT_QUALITY_PROMPT,
    "tech_summary": DEFAULT_TECH_SUMMARY_PROMPT,
    "trend_merge": DEFAULT_TREND_MERGE_PROMPT,
    "knowledge_update": DEFAULT_KNOWLEDGE_UPDATE_PROMPT,
}


def seed_defaults(db: Session) -> None:
    default_settings = {}
    for key, value in default_settings.items():
        if not db.query(AppSetting).filter(AppSetting.key == key).first():
            db.add(AppSetting(key=key, value=value))

    for prompt_type, content in PROMPT_TYPES.items():
        if not db.query(Prompt).filter(Prompt.type == prompt_type, Prompt.is_active.is_(True)).first():
            db.add(Prompt(type=prompt_type, content=content, is_active=True))

    default_labels = []
    for label_type, name in default_labels:
        exists = db.query(LabelDefinition).filter(LabelDefinition.type == label_type, LabelDefinition.name == name).first()
        if not exists:
            db.add(LabelDefinition(type=label_type, name=name, description=""))

    db.commit()
