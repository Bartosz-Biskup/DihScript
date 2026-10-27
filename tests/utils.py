from repositories.exceptions import NotFoundException
from repositories.models import Subscriber


class FakeLLMClient:
    def __init__(self, output: str = "") -> None:
        self.output = output
        self.last_prompt: str | None = None
        self.last_response_format: dict | None = None

    async def complete(self, prompt: str, response_format: dict | None = None) -> str:
        self.last_prompt = prompt
        self.last_response_format = response_format
        return self.output


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
