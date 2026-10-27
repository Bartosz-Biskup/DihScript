from typing import Protocol

from repositories.models import Subscriber
from repositories.subscriber_repository import SubscriberRepositoryProtocol

from .exceptions import AlreadyExistsException, NotFoundException


class SubscriberServiceProtocol(Protocol):
    def add_subscriber(self, name: str, email: str) -> Subscriber:
        ...

    def increase_run_count(self, email: str) -> Subscriber:
        ...


class SubscriberService(SubscriberServiceProtocol):
    def __init__(self, subscribers: SubscriberRepositoryProtocol) -> None:
        self._subscribers = subscribers

    def add_subscriber(self, name: str, email: str) -> Subscriber:
        if self._subscribers.get_by_email(email) is not None:
            raise AlreadyExistsException(f"Subscriber with email={email} already exists")

        subscriber = Subscriber(name=name, email=email, run_count=0)
        return self._subscribers.create(subscriber)

    def increase_run_count(self, email: str) -> Subscriber:
        subscriber = self._subscribers.get_by_email(email)
        if subscriber is None:
            raise NotFoundException(f"Subscriber with email={email} not found")

        subscriber.run_count += 1
        self._subscribers.update(subscriber)
        return subscriber
