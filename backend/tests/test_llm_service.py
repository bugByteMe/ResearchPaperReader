from types import SimpleNamespace

from app.services.llm_service import extract_chat_content


def test_extract_chat_content_from_openai_object():
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="对象响应"))]
    )

    assert extract_chat_content(response) == "对象响应"


def test_extract_chat_content_from_dict():
    response = {"choices": [{"message": {"content": "字典响应"}}]}

    assert extract_chat_content(response) == "字典响应"


def test_extract_chat_content_from_string():
    assert extract_chat_content("字符串响应") == "字符串响应"


def test_extract_chat_content_from_content_parts():
    response = {"choices": [{"message": {"content": [{"text": "分段"}, {"text": "响应"}]}}]}

    assert extract_chat_content(response) == "分段响应"
