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
    ModelProviderException,
)

logger = logging.getLogger(__name__)

DEEPSEEK_BASE_URL = "https://api.deepseek.com"

OutputFormat = TypeVar("OutputFormat", bound=BaseModel)


class LLMServiceProtocol(Protocol):
    async def complete(self, prompt: str, response_format: type[OutputFormat]) -> OutputFormat:
        ...


class LLMService:
    """Structured-output chat client (DeepSeek via instructor).

    ``complete`` sends the prompt and returns the reply parsed into
    ``response_format``. Failures are reported as:

    - :class:`EmptyPromptException` — blank prompt (caller's mistake, 400)
    - :class:`ModelProviderException` — provider unreachable or API error (502)
    - :class:`InvalidModelResponseException` — the reply never parsed into
      the expected shape, even after retries (502)

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
        response_format: type[OutputFormat],
    ) -> OutputFormat:
        if not prompt or not prompt.strip():
            raise EmptyPromptException("Cannot send an empty prompt to the model.")

        try:
            return await self._client.create(
                response_model=response_format,
                messages=[{"role": "user", "content": prompt}],
                max_retries=2,
            )
        except InstructorRetryException as exc:
            raise InvalidModelResponseException(
                f"The model repeatedly returned a reply that could not be parsed as "
                f"{response_format.__name__}: {exc}"
            ) from exc
        except (APIConnectionError, APITimeoutError, APIError) as exc:
            raise ModelProviderException(f"The model provider call failed: {exc}") from exc
