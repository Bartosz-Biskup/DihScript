import logging
import re
from os import environ
from typing import Protocol, TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError

from .config import MODEL
from .exceptions import (
    EmptyPromptException,
    EmptyResponseException,
    InvalidModelOutputException,
    LLMServiceException,
)

logger = logging.getLogger(__name__)

DEEPSEEK_BASE_URL = "https://api.deepseek.com"

OutputModel = TypeVar("OutputModel", bound=BaseModel)


class LLMServiceProtocol(Protocol):
    async def complete(
        self,
        prompt: str,
        response_format: type[BaseModel] | None = None,
    ) -> BaseModel | str:
        ...


class LLMService:
    """Chat client on the OpenAI SDK (DeepSeek endpoint by default).

    Two modes:

    - ``response_format`` given (a pydantic model class): the API is asked for
      a JSON object and the reply is parsed/validated into that model. Used by
      the script fixer (``PromptFixRequestOutput``).
    - ``response_format=None``: the raw reply text is returned as a string.
      Used by free-text consumers like the testing tool's judge.
    """

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str = DEEPSEEK_BASE_URL,
    ) -> None:
        self._model = model or MODEL
        api_key = api_key or environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            raise LLMServiceException("DEEPSEEK_API_KEY is not set (add it to .env)")

        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            max_retries=0,
            timeout=300.0,
        )

    async def complete(
        self,
        prompt: str,
        response_format: type[OutputModel] | None = None,
    ) -> OutputModel | str:
        if not prompt or not prompt.strip():
            raise EmptyPromptException("prompt must not be empty")

        kwargs = {"response_format": {"type": "json_object"}} if response_format else {}
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        )

        content = self._check_raw_llm_response(response)
        if response_format is None:
            return content
        return self._parse_content(content, response_format)

    @staticmethod
    def _check_raw_llm_response(response) -> str:
        choices = getattr(response, "choices", None)
        if not isinstance(choices, list) or len(choices) != 1:
            raise LLMServiceException("Expected exactly one response choice.")
        choice = choices[0]
        message = getattr(choice, "message", None)
        if (
            getattr(choice, "finish_reason", None) != "stop"
            or message is None
            or getattr(message, "role", None) != "assistant"
            or getattr(message, "tool_calls", None)
        ):
            raise LLMServiceException("Expected a completed text response.")
        content = getattr(message, "content", None)
        if not isinstance(content, str) or not content.strip():
            raise EmptyResponseException("model returned an empty response")
        return content

    @staticmethod
    def _parse_content(content: str, model: type[OutputModel]) -> OutputModel:
        text = content.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
        try:
            return model.model_validate_json(text)
        except ValidationError as e:
            raise InvalidModelOutputException("model returned invalid output") from e
