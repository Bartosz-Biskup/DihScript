from repositories.exceptions import NotFoundException
from repositories.models import Subscriber
from services.llm_service import LLMService


class FakeLLMClient:
    """Mimics LLMService.complete: parses its canned JSON into the requested
    model (or returns the raw text when no response_format is given)."""

    def __init__(self, output: str = "") -> None:
        self.output = output
        self.last_prompt: str | None = None
        self.last_response_format = None

    async def complete(self, prompt: str, response_format=None):
        self.last_prompt = prompt
        self.last_response_format = response_format
        if response_format is None:
            return self.output
        return LLMService._parse_content(self.output, response_format)


class FakeSubscriberRepo:
    def __init__(self, subscribers: list[Subscriber] | None = None) -> None:
        self._subscribers: dict[str, Subscriber] = {s.email: s for s in (subscribers or [])}

    def create(self, subscriber: Subscriber) -> Subscriber:
        self._subscribers[subscriber.email] = subscriber
        return subscriber

    def update(self, subscriber: Subscriber) -> None:
        if subscriber.email not in self._subscribers:
            raise NotFoundException(f"Subscriber with email={subscriber.email} not found")
        self._subscribers[subscriber.email] = subscriber

    def get_by_email(self, email: str) -> Subscriber | None:
        return self._subscribers.get(email)
