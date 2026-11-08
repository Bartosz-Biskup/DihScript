from typing import Protocol

import httpx

from repositories.models import PromptFixRequestOutput
from services.fix_facade import FixRequest


class FixApiException(Exception):
    ...


class FixApiClientProtocol(Protocol):
    async def fix(self, request: FixRequest) -> PromptFixRequestOutput:
        ...


class FixApiClient:
    """HTTP client for the main app's POST /fix endpoint."""

    def __init__(self, base_url: str, timeout: float = 180.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    async def fix(self, request: FixRequest) -> PromptFixRequestOutput:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(f"{self._base_url}/fix", json=request.model_dump())

        if response.status_code != 200:
            detail = response.text[:500].replace("\n", " ")
            raise FixApiException(f"fix api returned {response.status_code}: {detail}")

        return PromptFixRequestOutput.model_validate(response.json())
