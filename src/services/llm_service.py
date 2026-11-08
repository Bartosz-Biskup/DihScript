import logging
from os import environ
from typing import Protocol, TypeVar

import instructor
from instructor.core.exceptions import InstructorRetryException
from openai import APIConnectionError, APITimeoutError, APIError
from pydantic import BaseModel

from .config import MODEL
from .exceptions import (
    EmptyPromptException,
    InvalidModelResponseException,
    LLMException,
    ModelProviderException,
)

logger = logging.getLogger(__name__)

DEEPSEEK_BASE_URL = "https://api.deepseek.com"

OutputFormat = TypeVar("OutputFormat", bound=BaseModel)


class LLMServiceProtocol(Protocol):
    async def complete(
        self,
        prompt: str,
        response_format: type[OutputFormat] | None = None,
    ) -> OutputFormat | str:
        ...


class LLMService:
    """Chat client on the instructor SDK (DeepSeek endpoint).

    Two modes:

    - ``response_format`` given (a pydantic model class): the reply is parsed
      into that model, with retries when the model returns unparsable JSON.
    - ``response_format=None``: the raw reply text is returned as a string
      (used by free-text consumers like the testing tool's judge).

    Failures are reported as:

    - :class:`EmptyPromptException` — blank prompt (caller's mistake, 400)
    - :class:`ModelProviderException` — provider unreachable or API error (502)
    - :class:`InvalidModelResponseException` — the reply never parsed into
      the expected shape, even after retries (502)
    - :class:`LLMException` — an empty free-text reply (502)

    Unexpected exceptions (programming errors) are deliberately *not*
    wrapped — they propagate and surface as 500, where they belong.
    """

    def __init__(
        self,
        model: str | None = None,
        client: instructor.AsyncInstructor | None = None,
    ) -> None:
        self._model = model or MODEL

        if client is not None:
            self._client = client
            return

        api_key = environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            raise ModelProviderException(
                "DEEPSEEK_API_KEY is not set. Add it to the .env file and restart the app."
            )

        self._client = instructor.from_provider(
            model=f"deepseek/{self._model}",
            async_client=True,
            api_key=api_key,
            base_url=DEEPSEEK_BASE_URL,
        )

    async def complete(
        self,
        prompt: str,
        response_format: type[OutputFormat] | None = None,
        max_tokens: int | None = None,
    ) -> OutputFormat | str:
        """Send the prompt to the model.

        ``max_tokens`` caps the length of the model's reply (output tokens);
        it is passed straight to the provider and is the main lever for
        controlling token spend on verbose consumers like the judge.
        """
        if not prompt or not prompt.strip():
            raise EmptyPromptException("Cannot send an empty prompt to the model.")

        if response_format is None:
            return await self._complete_text(prompt, max_tokens)

        kwargs = {"max_tokens": max_tokens} if max_tokens else {}
        try:
            return await self._client.create(
                response_model=response_format,
                messages=[{"role": "user", "content": prompt}],
                max_retries=2,
                **kwargs,
            )
        except InstructorRetryException as exc:
            raise InvalidModelResponseException(
                f"The model repeatedly returned a reply that could not be parsed as "
                f"{response_format.__name__}: {exc}"
            ) from exc
        except (APIConnectionError, APITimeoutError, APIError) as exc:
            raise ModelProviderException(f"The model provider call failed: {exc}") from exc

    async def _complete_text(self, prompt: str, max_tokens: int | None = None) -> str:
        kwargs = {"max_tokens": max_tokens} if max_tokens else {}
        try:
            response = await self._client.create(
                response_model=None,
                messages=[{"role": "user", "content": prompt}],
                max_retries=0,
                **kwargs,
            )
        except (APIConnectionError, APITimeoutError, APIError) as exc:
            raise ModelProviderException(f"The model provider call failed: {exc}") from exc

        choices = getattr(response, "choices", None)
        if not isinstance(choices, list) or not choices:
            raise LLMException("The model returned no usable text.")

        content = getattr(choices[0].message, "content", None)
        if not isinstance(content, str) or not content.strip():
            raise LLMException("The model returned an empty reply.")

        return content
