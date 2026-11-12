import pytest
from fastapi.testclient import TestClient

import services.prompt_fixer_service as pfs_module
from api.dependencies import get_fix_facade, get_subscriber_service
from api.main import app
from api.rate_limiter import CONFIG, RateLimiterConfig
from repositories.models import PromptFixRequestOutput, Subscriber
from services.fix_facade import FixFacade
from services.prompt_fixer_service import PromptFixerService
from services.subscriber_service import SubscriberService
from utils import FakeLLMClient, FakeSubscriberRepo


_TEMPLATE = (
    "<role>ROLE</role>\n\n"
    "<script_writing_guidelines>TODO</script_writing_guidelines>\n\n"
    "<output_format>OUTPUT FORMAT</output_format>\n\n"
    "<security>SECURITY</security>\n\n"
    "<user_content>\n{{USER_CONTENT}}\n</user_content>"
)

_VALID_OUTPUT = PromptFixRequestOutput(
    script="fixed",
    info="ok",
    error=None,
    changes=[],
)


@pytest.fixture()
def subscriber_repo():
    return FakeSubscriberRepo()


def make_client(tmp_path, monkeypatch, repo: FakeSubscriberRepo) -> TestClient:
    (tmp_path / "script_fixer.txt").write_text(_TEMPLATE, encoding="utf-8")
    monkeypatch.setattr(pfs_module, "PROMPTS_DIR", tmp_path)

    subscriber_service = SubscriberService(repo)
    fixer = PromptFixerService(FakeLLMClient(_VALID_OUTPUT))
    fix_facade = FixFacade(fixer=fixer, subscribers=subscriber_service)

    app.dependency_overrides[get_fix_facade] = lambda: fix_facade
    app.dependency_overrides[get_subscriber_service] = lambda: subscriber_service
    return TestClient(app)


def _subscriber_payload(i: int) -> dict:
    return {"name": f"Mark{i}", "email": f"mark{i}@gmail.com"}


def _fix_payload() -> dict:
    return {"email": "anna@example.com", "script": "hi", "mode": "watch", "length": 30}


def test_rate_limiter_config_formats_slowapi_string():
    config = RateLimiterConfig(limit=3, period="minute")
    assert config.get_limiter_config_in_slowapi_format() == "3/minute"


def test_subscriber_requests_up_to_the_limit_are_allowed(tmp_path, monkeypatch, subscriber_repo):
    client = make_client(tmp_path, monkeypatch, subscriber_repo)

    for i in range(CONFIG["subscriber_router"].limit):
        response = client.post("/subscriber", json=_subscriber_payload(i))
        assert response.status_code == 201


def test_subscriber_raises_429_once_limit_is_exceeded(tmp_path, monkeypatch, subscriber_repo):
    client = make_client(tmp_path, monkeypatch, subscriber_repo)

    for i in range(CONFIG["subscriber_router"].limit):
        client.post("/subscriber", json=_subscriber_payload(i))

    response = client.post("/subscriber", json=_subscriber_payload(99))

    assert response.status_code == 429
    assert "rate limit" in response.json()["error"].lower()


def test_fix_requests_up_to_the_limit_are_allowed(tmp_path, monkeypatch, subscriber_repo):
    subscriber_repo.create(Subscriber(name="Anna", email="anna@example.com", run_count=0))
    client = make_client(tmp_path, monkeypatch, subscriber_repo)

    for _ in range(CONFIG["fix_router"].limit):
        response = client.post("/fix", json=_fix_payload())
        assert response.status_code == 200


def test_fix_raises_429_once_limit_is_exceeded(tmp_path, monkeypatch, subscriber_repo):
    subscriber_repo.create(Subscriber(name="Anna", email="anna@example.com", run_count=0))
    client = make_client(tmp_path, monkeypatch, subscriber_repo)

    for _ in range(CONFIG["fix_router"].limit):
        client.post("/fix", json=_fix_payload())

    response = client.post("/fix", json=_fix_payload())

    assert response.status_code == 429
    assert "rate limit" in response.json()["error"].lower()


def test_endpoint_budgets_are_counted_independently(tmp_path, monkeypatch, subscriber_repo):
    subscriber_repo.create(Subscriber(name="Anna", email="anna@example.com", run_count=0))
    client = make_client(tmp_path, monkeypatch, subscriber_repo)

    for i in range(CONFIG["subscriber_router"].limit + 1):
        client.post("/subscriber", json=_subscriber_payload(i))  # budżet subskrybenta wyczerpany

    response = client.post("/fix", json=_fix_payload())

    assert response.status_code == 200  # budżet fixa nietknięty
