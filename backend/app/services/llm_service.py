from openai import OpenAI

from app.config import settings


def extract_chat_content(response: object) -> str:
    if isinstance(response, str):
        return response

    if isinstance(response, dict):
        choices = response.get("choices")
        if choices:
            message = choices[0].get("message", {})
            content = message.get("content", "")
            return normalize_content(content)
        return normalize_content(response.get("content", ""))

    choices = getattr(response, "choices", None)
    if choices:
        message = getattr(choices[0], "message", None)
        content = getattr(message, "content", "") if message else ""
        return normalize_content(content)

    return normalize_content(getattr(response, "content", ""))


def normalize_content(content: object) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("content") or ""))
            else:
                parts.append(str(item))
        return "".join(parts)
    return str(content)


class LLMClient:
    def __init__(self) -> None:
        self.client = OpenAI(base_url=settings.openai_base_url, api_key=settings.openai_api_key)

    def analyze(self, prompt: str, paper_context: str) -> str:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")

        response = self.client.chat.completions.create(
            model=settings.openai_model,
            temperature=settings.openai_temperature,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": paper_context},
            ],
        )
        return extract_chat_content(response)


def build_paper_context(title: str, abstract: str, authors: str, pdf_text: str) -> str:
    text = pdf_text[: settings.analysis_max_text_chars]
    return f"""Title: {title}
Authors: {authors}

Abstract:
{abstract}

PDF full text excerpt for analysis:
{text}"""
