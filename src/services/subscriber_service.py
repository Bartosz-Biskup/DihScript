from typing import Protocol

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from repositories.models import Subscriber
from repositories.subscriber_repository import SubscriberRepositoryProtocol

from .exceptions import NotFoundException


class SubscriberCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1)
    email: EmailStr


class SubscriberServiceProtocol(Protocol):
    def register_subscriber(self, name: str, email: str) -> Subscriber:
        ...

    def get_subscriber(self, email: str) -> Subscriber:
        ...

    def increase_run_count(self, email: str) -> Subscriber:
        ...


class SubscriberService(SubscriberServiceProtocol):
    def __init__(self, subscribers: SubscriberRepositoryProtocol) -> None:
        self._subscribers = subscribers

    def register_subscriber(self, name: str, email: str) -> Subscriber:
        if self._subscribers.get_by_email(email) is not None:
            return self.increase_run_count(email)

        subscriber = Subscriber(name=name, email=email, run_count=0)
        return self._subscribers.create(subscriber)

    def get_subscriber(self, email: str) -> Subscriber:
        subscriber = self._subscribers.get_by_email(email)
        if subscriber is None:
            raise NotFoundException(f"Subscriber with email={email} not found")

        return subscriber

    def increase_run_count(self, email: str) -> Subscriber:
        subscriber = self.get_subscriber(email)

        subscriber.run_count += 1
        self._subscribers.update(subscriber)
        return subscriber
