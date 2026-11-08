from typing import Protocol

from sqlalchemy.orm import Session

from database.tables import SubscriberTable

from .exceptions import NotFoundException
from .models import Subscriber


class SubscriberRepositoryProtocol(Protocol):
    def create(self, subscriber: Subscriber) -> Subscriber:
        ...

    def update(self, subscriber: Subscriber) -> None:
        ...

    def get_by_email(self, email: str) -> Subscriber | None:
        ...


class SubscriberRepository(SubscriberRepositoryProtocol):
    def __init__(self, session: Session) -> None:
        self._session = session

    def _to_orm(self, subscriber: Subscriber) -> SubscriberTable:
        return SubscriberTable(
            name=subscriber.name,
            email=subscriber.email,
            run_count=subscriber.run_count,
        )

    def _to_domain(self, table: SubscriberTable) -> Subscriber:
        return Subscriber(
            name=table.name,
            email=table.email,
            run_count=table.run_count,
        )

    def create(self, subscriber: Subscriber) -> Subscriber:
        orm_subscriber = self._to_orm(subscriber)
        self._session.add(orm_subscriber)
        self._session.flush()
        return self._to_domain(orm_subscriber)

    def update(self, subscriber: Subscriber) -> None:
        orm_subscriber = self._session.get(SubscriberTable, subscriber.email)
        if orm_subscriber is None:
            raise NotFoundException(
                f"No subscriber with email '{subscriber.email}' is registered."
            )

        orm_subscriber.name = subscriber.name
        orm_subscriber.run_count = subscriber.run_count
        self._session.flush()

    def get_by_email(self, email: str) -> Subscriber | None:
        orm_subscriber = self._session.get(SubscriberTable, email)
        if orm_subscriber is None:
            return None

        return self._to_domain(orm_subscriber)
