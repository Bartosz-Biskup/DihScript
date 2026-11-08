from fastapi.testclient import TestClient

import services.prompt_fixer_service as pfs_module
from api.dependencies import get_fix_facade
from api.main import app
from repositories.models import Subscriber, PromptFixRequestOutput
from services.fix_facade import FixFacade
from services.prompt_fixer_service import PromptFixerService
from services.subscriber_service import SubscriberService
from utils import FakeLLMClient, FakeSubscriberRepo

_VALID_OUTPUT = PromptFixRequestOutput(
    script="fixed",
    info="ok",
    error=None,
    changes=[]
)

_TEMPLATE = (
    "<role>ROLE</role>\n\n"
    "<script_writing_guidelines>TODO</script_writing_guidelines>\n\n"
    "<output_format>OUTPUT FORMAT</output_format>\n\n"
    "<security>SECURITY</security>\n\n"
    "<user_content>\n{{USER_CONTENT}}\n</user_content>"
)


def make_subscriber(name: str = "Anna", email: str = "anna@example.com", run_count: int = 0) -> Subscriber:
    return Subscriber(name=name, email=email, run_count=run_count)


def make_client(tmp_path, monkeypatch, repo: FakeSubscriberRepo) -> TestClient:
    (tmp_path / "script_fixer.txt").write_text(_TEMPLATE, encoding="utf-8")
    monkeypatch.setattr(pfs_module, "PROMPTS_DIR", tmp_path)

    fixer = PromptFixerService(FakeLLMClient(_VALID_OUTPUT))
    service = FixFacade(fixer, SubscriberService(repo))
    app.dependency_overrides[get_fix_facade] = lambda: service
    return TestClient(app)


def test_fix_returns_output_and_increments_run_count(tmp_path, monkeypatch):
    repo = FakeSubscriberRepo([make_subscriber()])
    client = make_client(tmp_path, monkeypatch, repo)

    response = client.post("/fix", json={"email": "anna@example.com", "script": "hi"})

    assert response.status_code == 200
    assert response.json()["script"] == "fixed"
    assert repo.get_by_email("anna@example.com").run_count == 1


def test_fix_unknown_email_returns_404(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch, FakeSubscriberRepo())

    response = client.post("/fix", json={"email": "missing@example.com", "script": "hi"})

    assert response.status_code == 404


def test_fix_sell_mode_without_audience_returns_422(tmp_path, monkeypatch):
    repo = FakeSubscriberRepo([make_subscriber()])
    client = make_client(tmp_path, monkeypatch, repo)

    response = client.post(
        "/fix",
        json={"email": "anna@example.com", "script": "hi", "mode": "sell"},
    )

    assert response.status_code == 422


def test_fix_invalid_email_returns_422(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch, FakeSubscriberRepo())

    response = client.post("/fix", json={"email": "not-an-email", "script": "hi"})

    assert response.status_code == 422
