import asyncio

import pytest

import services.llm_service as llm_module
from services.exceptions import EmptyPromptException, EmptyResponseException
from services.llm_service import LLMService


class _Message:
    def __init__(self, content: str) -> None:
        self.content = content


class _Choice:
    def __init__(self, content: str) -> None:
        self.message = _Message(content)


class _Response:
    def __init__(self, content: str) -> None:
        self.choices = [_Choice(content)]


@pytest.mark.parametrize("bad", ["", "   ", "\n\t"])
def test_empty_prompt_raises(bad):
    with pytest.raises(EmptyPromptException):
        asyncio.run(LLMService().complete(bad))


def test_response_format_is_passed_through(monkeypatch):
    captured: dict = {}

    async def fake_acompletion(**kwargs):
        captured.update(kwargs)
        return _Response("ok")

    monkeypatch.setattr(llm_module, "acompletion", fake_acompletion)
    asyncio.run(LLMService().complete("hi", response_format={"type": "json_object"}))
    assert captured["response_format"] == {"type": "json_object"}
    assert captured["messages"][0]["content"] == "hi"


def test_empty_response_raises(monkeypatch):
    async def fake_acompletion(**kwargs):
        return _Response("")

    monkeypatch.setattr(llm_module, "acompletion", fake_acompletion)
    with pytest.raises(EmptyResponseException):
        asyncio.run(LLMService().complete("hi"))
