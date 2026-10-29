from fastapi.testclient import TestClient

from api.dependencies import get_subscriber_service
from api.main import app
from repositories.models import Subscriber
from services.subscriber_service import SubscriberService
from utils import FakeSubscriberRepo


def make_subscriber(name: str = "Anna", email: str = "anna@example.com", run_count: int = 0) -> Subscriber:
    return Subscriber(name=name, email=email, run_count=run_count)


def make_client(repo: FakeSubscriberRepo) -> TestClient:
    app.dependency_overrides[get_subscriber_service] = lambda: SubscriberService(repo)
    return TestClient(app)


def test_register_subscriber_returns_201_with_subscriber():
    repo = FakeSubscriberRepo()
    client = make_client(repo)

    response = client.post("/subscriber", json={"name": "Anna", "email": "anna@example.com"})

    assert response.status_code == 201
    assert response.json() == {"name": "Anna", "email": "anna@example.com", "run_count": 0}
    assert repo.get_by_email("anna@example.com").name == "Anna"


def test_register_subscriber_existing_email_increments_run_count():
    repo = FakeSubscriberRepo([make_subscriber()])
    client = make_client(repo)

    response = client.post("/subscriber", json={"name": "Other", "email": "anna@example.com"})

    assert response.status_code == 201
    assert response.json() == {"name": "Anna", "email": "anna@example.com", "run_count": 1}
    assert repo.get_by_email("anna@example.com").run_count == 1


def test_register_subscriber_empty_name_returns_422():
    client = make_client(FakeSubscriberRepo())

    response = client.post("/subscriber", json={"name": "", "email": "anna@example.com"})

    assert response.status_code == 422


def test_register_subscriber_invalid_email_returns_422():
    client = make_client(FakeSubscriberRepo())

    response = client.post("/subscriber", json={"name": "Anna", "email": "not-an-email"})

    assert response.status_code == 422


def test_register_subscriber_normalizes_email():
    repo = FakeSubscriberRepo()
    client = make_client(repo)

    response = client.post("/subscriber", json={"name": "Anna", "email": "anna@Example.COM"})

    assert response.status_code == 201
    assert response.json()["email"] == "anna@example.com"
    assert repo.get_by_email("anna@example.com") is not None
