import asyncio

import pytest
from instructor.core.exceptions import InstructorRetryException
from openai import APIConnectionError, APITimeoutError, APIError
from pydantic import ValidationError

from repositories.models import PromptFixRequestOutput
from services.exceptions import (
    EmptyPromptException,
    InvalidModelResponseException,
    ModelProviderException,
)
from services.llm_service import LLMService


class _FakeInstructorClient:
    """Stands in for the instructor client; records calls, returns a canned
    result or raises a canned error."""

    def __init__(self, result=None, error=None):
        self._result = result
        self._error = error
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        if self._error is not None:
            raise self._error
        return self._result


def make_service(client) -> LLMService:
    # A client is injected, so no API key is needed and no network is touched.
    return LLMService(model="deepseek-chat", client=client)


def _bare(exception_class):
    """An exception instance built without running its constructor.

    The openai SDK exceptions require httpx2.Request objects; the tests only
    care about the isinstance matching, so skip __init__ entirely.
    """
    return exception_class.__new__(exception_class)


@pytest.mark.parametrize("bad", ["", "   ", "\n\t"])
def test_empty_prompt_raises_without_calling_the_provider(bad):
    client = _FakeInstructorClient(result=PromptFixRequestOutput(script="s", info="i"))
    service = make_service(client)

    with pytest.raises(EmptyPromptException, match="empty prompt"):
        asyncio.run(service.complete(bad, PromptFixRequestOutput))

    assert client.calls == []


def test_missing_api_key_raises_a_clear_error(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    with pytest.raises(ModelProviderException, match="DEEPSEEK_API_KEY"):
        LLMService(model="deepseek-chat")


def test_valid_reply_returns_the_parsed_model():
    output = PromptFixRequestOutput(script="fixed", info="ok")
    client = _FakeInstructorClient(result=output)
    service = make_service(client)

    result = asyncio.run(service.complete("fix this", PromptFixRequestOutput))

    assert result is output
    call = client.calls[0]
    assert call["response_model"] is PromptFixRequestOutput
    assert call["messages"] == [{"role": "user", "content": "fix this"}]
    assert call["max_retries"] == 2


def test_retries_exhausted_become_invalid_model_response():
    error = InstructorRetryException("retries exhausted", n_attempts=3, total_usage=0)
    client = _FakeInstructorClient(error=error)
    service = make_service(client)

    with pytest.raises(InvalidModelResponseException, match="could not be parsed"):
        asyncio.run(service.complete("fix this", PromptFixRequestOutput))


@pytest.mark.parametrize(
    "provider_error",
    [
        _bare(APIConnectionError),
        _bare(APITimeoutError),
        _bare(APIError),
    ],
)
def test_provider_failures_become_model_provider_exception(provider_error):
    client = _FakeInstructorClient(error=provider_error)
    service = make_service(client)

    with pytest.raises(ModelProviderException, match="provider call failed"):
        asyncio.run(service.complete("fix this", PromptFixRequestOutput))


def test_unexpected_errors_are_not_wrapped():
    # Programming errors must stay visible instead of being relabeled as
    # provider failures.
    client = _FakeInstructorClient(error=RuntimeError("a bug in our code"))
    service = make_service(client)

    with pytest.raises(RuntimeError, match="a bug in our code"):
        asyncio.run(service.complete("fix this", PromptFixRequestOutput))


def test_validation_errors_from_the_client_are_not_wrapped():
    client = _FakeInstructorClient(error=ValidationError.from_exception_data("x", []))
    service = make_service(client)

    with pytest.raises(ValidationError):
        asyncio.run(service.complete("fix this", PromptFixRequestOutput))
