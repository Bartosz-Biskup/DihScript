import asyncio

import pytest

from repositories.models import PromptFixRequestOutput
from services.exceptions import (
    EmptyPromptException,
    EmptyResponseException,
    InvalidModelOutputException,
    LLMServiceException,
)
from services.llm_service import LLMService


class _Message:
    def __init__(self, content=None, role="assistant", tool_calls=None):
        self.content = content
        self.role = role
        self.tool_calls = tool_calls


class _Choice:
    def __init__(self, message, finish_reason="stop"):
        self.message = message
        self.finish_reason = finish_reason


class _Response:
    def __init__(self, choices):
        self.choices = choices


class _Completions:
    def __init__(self, responder):
        self._responder = responder
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return self._responder()


class _Chat:
    def __init__(self, completions):
        self.completions = completions


class _FakeClient:
    def __init__(self, responder):
        self.chat = _Chat(_Completions(responder))


_VALID_JSON = '{"script": "fixed", "info": "ok", "error": null, "changes": []}'


def make_service(responder=None) -> tuple[LLMService, _Completions]:
    service = LLMService(model="deepseek-chat", api_key="test-key")
    client = _FakeClient(responder or (lambda: _Response([_Choice(_Message(_VALID_JSON))])))
    service._client = client
    return service, client.chat.completions


@pytest.mark.parametrize("bad", ["", "   ", "\n\t"])
def test_empty_prompt_raises(bad):
    service, _ = make_service()
    with pytest.raises(EmptyPromptException):
        asyncio.run(service.complete(bad, response_format=PromptFixRequestOutput))


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with pytest.raises(LLMServiceException, match="DEEPSEEK_API_KEY"):
        LLMService(model="deepseek-chat", api_key=None)


def test_valid_json_returns_parsed_model():
    service, completions = make_service()

    result = asyncio.run(
        service.complete("fix this", response_format=PromptFixRequestOutput)
    )

    assert isinstance(result, PromptFixRequestOutput)
    assert result.script == "fixed"
    assert result.info == "ok"
    assert result.changes == []

    call = completions.calls[0]
    assert call["model"] == "deepseek-chat"
    assert call["messages"] == [{"role": "user", "content": "fix this"}]
    assert call["response_format"] == {"type": "json_object"}


def test_fenced_json_is_parsed():
    fenced = '```json\n' + _VALID_JSON + '\n```'
    service, _ = make_service(lambda: _Response([_Choice(_Message(fenced))]))

    result = asyncio.run(
        service.complete("fix this", response_format=PromptFixRequestOutput)
    )

    assert result.script == "fixed"


def test_invalid_json_raises():
    service, _ = make_service(lambda: _Response([_Choice(_Message("not json"))]))

    with pytest.raises(InvalidModelOutputException):
        asyncio.run(service.complete("fix this", response_format=PromptFixRequestOutput))


def test_wrong_fields_raise_validation_error():
    wrong = '{"script": 123, "info": "ok", "error": null, "changes": []}'
    service, _ = make_service(lambda: _Response([_Choice(_Message(wrong))]))

    with pytest.raises(InvalidModelOutputException):
        asyncio.run(service.complete("fix this", response_format=PromptFixRequestOutput))


def test_empty_content_raises():
    service, _ = make_service(lambda: _Response([_Choice(_Message(""))]))

    with pytest.raises(EmptyResponseException):
        asyncio.run(service.complete("fix this", response_format=PromptFixRequestOutput))


@pytest.mark.parametrize(
    "bad_response",
    [
        _Response([]),  # no choices
        _Response([_Choice(_Message(_VALID_JSON)), _Choice(_Message(_VALID_JSON))]),
        _Response([_Choice(_Message(_VALID_JSON), finish_reason="length")]),
        _Response([_Choice(_Message(_VALID_JSON, role="user"))]),
        _Response([_Choice(_Message(_VALID_JSON, tool_calls=[{"id": "t1"}]))]),
        _Response([_Choice(_Message(None))]),  # content is None
    ],
)
def test_malformed_provider_response_raises(bad_response):
    service, _ = make_service(lambda: bad_response)

    with pytest.raises((LLMServiceException, EmptyResponseException)):
        asyncio.run(service.complete("fix this", response_format=PromptFixRequestOutput))


def test_no_response_format_returns_raw_text():
    service, completions = make_service()

    result = asyncio.run(service.complete("rate this"))

    assert result == _VALID_JSON
    assert "response_format" not in completions.calls[0]
