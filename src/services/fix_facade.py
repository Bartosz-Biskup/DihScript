from typing import Protocol

from pydantic import EmailStr

from repositories.models import PromptFixRequestInput, PromptFixRequestOutput

from .prompt_fixer_service import PromptFixerServiceProtocol
from .subscriber_service import SubscriberServiceProtocol


class FixRequest(PromptFixRequestInput):
    email: EmailStr


class FixFacadeProtocol(Protocol):
    async def fix(self, request: FixRequest) -> PromptFixRequestOutput:
        ...


class FixFacade(FixFacadeProtocol):
    def __init__(
        self,
        fixer: PromptFixerServiceProtocol,
        subscribers: SubscriberServiceProtocol,
    ) -> None:
        self._fixer = fixer
        self._subscribers = subscribers

    async def fix(self, request: FixRequest) -> PromptFixRequestOutput:
        self._subscribers.get_subscriber(request.email)

        output = await self._fixer.fix(request)
        self._subscribers.increase_run_count(request.email)
        return output
