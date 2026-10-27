import pytest

from repositories.models import Subscriber
from services.exceptions import AlreadyExistsException, NotFoundException
from services.subscriber_service import SubscriberService
from utils import FakeSubscriberRepo


def make_subscriber(name: str = "Anna", email: str = "anna@example.com", run_count: int = 0) -> Subscriber:
    return Subscriber(name=name, email=email, run_count=run_count)


def build_service(repo: FakeSubscriberRepo | None = None) -> SubscriberService:
    return SubscriberService(repo or FakeSubscriberRepo())


def test_add_subscriber_creates_with_zero_runs():
    repo = FakeSubscriberRepo()
    service = build_service(repo)

    created = service.add_subscriber("Anna", "anna@example.com")

    assert created.name == "Anna"
    assert created.email == "anna@example.com"
    assert created.run_count == 0
    assert repo.get_by_email("anna@example.com") == created


def test_add_subscriber_duplicate_email_raises():
    repo = FakeSubscriberRepo([make_subscriber()])
    service = build_service(repo)

    with pytest.raises(AlreadyExistsException):
        service.add_subscriber("Other", "anna@example.com")


def test_increase_run_count_increments():
    repo = FakeSubscriberRepo([make_subscriber()])
    service = build_service(repo)

    updated = service.increase_run_count("anna@example.com")

    assert updated.run_count == 1
    assert repo.get_by_email("anna@example.com").run_count == 1


def test_increase_run_count_accumulates():
    repo = FakeSubscriberRepo([make_subscriber(run_count=4)])
    service = build_service(repo)

    updated = service.increase_run_count("anna@example.com")

    assert updated.run_count == 5


def test_increase_run_count_unknown_email_raises():
    service = build_service(FakeSubscriberRepo())

    with pytest.raises(NotFoundException):
        service.increase_run_count("missing@example.com")
