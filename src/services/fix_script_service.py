from typing import Protocol

from pydantic import Field

from repositories.models import PromptFixRequest, PromptFixRequestOutput

from .prompt_fixer_service import PromptFixerServiceProtocol
from .subscriber_service import SubscriberServiceProtocol


class FixScriptRequest(PromptFixRequest):
    email: str = Field(min_length=1)


class FixScriptServiceProtocol(Protocol):
    async def fix_script(self, request: FixScriptRequest) -> PromptFixRequestOutput:
        ...


class FixScriptService(FixScriptServiceProtocol):
    def __init__(
        self,
        fixer: PromptFixerServiceProtocol,
        subscribers: SubscriberServiceProtocol,
    ) -> None:
        self._fixer = fixer
        self._subscribers = subscribers

    async def fix_script(self, request: FixScriptRequest) -> PromptFixRequestOutput:
        self._subscribers.get_subscriber(request.email)

        output = await self._fixer.fix(request)
        self._subscribers.increase_run_count(request.email)
        return output
