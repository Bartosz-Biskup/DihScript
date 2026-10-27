from typing import Protocol

from litellm import acompletion

from .config import MODEL
from .exceptions import EmptyPromptException, EmptyResponseException


class LLMServiceProtocol(Protocol):
    async def complete(self, prompt: str, response_format: dict | None = None) -> str:
        ...


class LLMService:
    def __init__(self, model: str | None = None) -> None:
        self._model = model or MODEL

    async def complete(self, prompt: str, response_format: dict | None = None) -> str:
        if not prompt or not prompt.strip():
            raise EmptyPromptException("prompt must not be empty")

        kwargs = {"response_format": response_format} if response_format else {}
        resp = await acompletion(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        )
        text = resp.choices[0].message.content
        if not text:
            raise EmptyResponseException("model returned an empty response")
        return text
