import pytest

from repositories.models import Subscriber
from services.exceptions import NotFoundException
from services.subscriber_service import SubscriberService
from utils import FakeSubscriberRepo


def make_subscriber(name: str = "Anna", email: str = "anna@example.com", run_count: int = 0) -> Subscriber:
    return Subscriber(name=name, email=email, run_count=run_count)


def build_service(repo: FakeSubscriberRepo | None = None) -> SubscriberService:
    return SubscriberService(repo or FakeSubscriberRepo())


def test_register_subscriber_creates_with_zero_runs():
    repo = FakeSubscriberRepo()
    service = build_service(repo)

    created = service.register_subscriber("Anna", "anna@example.com")

    assert created.name == "Anna"
    assert created.email == "anna@example.com"
    assert created.run_count == 0
    assert repo.get_by_email("anna@example.com") == created


def test_register_subscriber_existing_email_increments_run_count():
    repo = FakeSubscriberRepo([make_subscriber()])
    service = build_service(repo)

    updated = service.register_subscriber("Other", "anna@example.com")

    assert updated.name == "Anna"
    assert updated.email == "anna@example.com"
    assert updated.run_count == 1
    assert repo.get_by_email("anna@example.com").run_count == 1


def test_register_subscriber_existing_email_accumulates():
    repo = FakeSubscriberRepo([make_subscriber(run_count=4)])
    service = build_service(repo)

    updated = service.register_subscriber("Anna", "anna@example.com")

    assert updated.run_count == 5


def test_get_subscriber_returns_existing():
    repo = FakeSubscriberRepo([make_subscriber()])
    service = build_service(repo)

    found = service.get_subscriber("anna@example.com")

    assert found.name == "Anna"
    assert found.email == "anna@example.com"


def test_get_subscriber_unknown_raises():
    service = build_service(FakeSubscriberRepo())

    with pytest.raises(NotFoundException):
        service.get_subscriber("missing@example.com")


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
