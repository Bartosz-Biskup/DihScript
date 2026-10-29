import time

import pytest
from fastapi.testclient import TestClient

from testing.api.dependencies import get_job_manager, get_testing_service
from testing.database import Database
from testing.main import app
from testing.services.job_manager import JobManager
from testing.services.testing_service import TestingService as Service
from tests.testing_utils import BusyJobManager, FakeFixClient, FakeJudge, make_output

MANUAL_PAYLOAD = {
    "email": "anna@example.com",
    "mode": "watch",
    "script": "ORIGINAL SCRIPT",
    "length": 30,
}

GROUP_PAYLOAD = {
    "name": "batch-1",
    "email": "anna@example.com",
    "items": [
        {"mode": "watch", "script": "script A", "length": 30},
        {"mode": "watch", "script": "script B", "length": 60},
    ],
}


@pytest.fixture
def client(tmp_path):
    db = Database(f"sqlite:///{tmp_path}/testing.db")
    db.create_all()
    fix = FakeFixClient()
    judge = FakeJudge(verdict="ok verdict")
    service = Service(db, fix, judge)

    app.dependency_overrides[get_testing_service] = lambda: service
    job_manager = JobManager()
    app.dependency_overrides[get_job_manager] = lambda: job_manager
    with TestClient(app) as test_client:
        yield test_client, service, fix, judge
    app.dependency_overrides.clear()


def wait_until_done(client: TestClient, group_id: int, timeout: float = 10.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        group = client.get(f"/testing/api/groups/{group_id}").json()
        if group["status"] == "done":
            return group
        time.sleep(0.05)
    raise AssertionError("group did not finish in time")


def test_index_serves_the_ui(client):
    test_client, _, _, _ = client

    response = test_client.get("/testing/")

    assert response.status_code == 200
    assert "Fixer testing tool" in response.text


def test_manual_execute_returns_output_and_verdict_without_saving(client):
    test_client, _, _, judge = client

    response = test_client.post("/testing/api/runs", json=MANUAL_PAYLOAD)

    assert response.status_code == 200
    data = response.json()
    assert data["output"]["script"] == "FIXED SCRIPT"
    assert data["verdict"] == "ok verdict"
    assert judge.judge_calls == 1

    runs = test_client.get("/testing/api/runs").json()
    assert runs["total"] == 0


def test_manual_execute_rejected_while_job_is_busy(client):
    test_client, _, _, _ = client
    app.dependency_overrides[get_job_manager] = lambda: BusyJobManager()

    response = test_client.post("/testing/api/runs", json=MANUAL_PAYLOAD)

    assert response.status_code == 409
    assert "in progress" in response.json()["detail"]


def test_manual_save_and_fetch_run(client):
    test_client, _, _, _ = client
    output = make_output()

    save_response = test_client.post(
        "/testing/api/runs/save",
        json={"input": MANUAL_PAYLOAD, "output": output.model_dump(), "verdict": "nice"},
    )
    assert save_response.status_code == 201
    run_id = save_response.json()["id"]

    detail = test_client.get(f"/testing/api/runs/{run_id}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["script"] == "ORIGINAL SCRIPT"
    assert body["fixed_script"] == "FIXED SCRIPT"
    assert body["verdict"] == "nice"
    assert body["group_id"] is None
    assert len(body["changes"]) == 1

    runs = test_client.get("/testing/api/runs").json()
    assert runs["total"] == 1


def test_manual_save_invalid_payload_returns_422(client):
    test_client, _, _, _ = client

    response = test_client.post("/testing/api/runs/save", json={"input": {"email": "x"}})

    assert response.status_code == 422


def test_create_group_and_list_runs(client):
    test_client, _, _, _ = client

    create = test_client.post("/testing/api/groups", json=GROUP_PAYLOAD)
    assert create.status_code == 201
    group = create.json()
    assert group["status"] == "pending"
    assert group["total_runs"] == 2

    groups = test_client.get("/testing/api/groups").json()
    assert [g["id"] for g in groups["groups"]] == [group["id"]]

    runs = test_client.get(f"/testing/api/groups/{group['id']}/runs").json()
    assert runs["total"] == 2
    assert all(r["status"] == "pending" for r in runs["runs"])


def test_create_group_requires_valid_items(client):
    test_client, _, _, _ = client

    bad = dict(GROUP_PAYLOAD, items=[{"mode": "watch", "script": ""}])
    assert test_client.post("/testing/api/groups", json=bad).status_code == 422

    empty = dict(GROUP_PAYLOAD, items=[])
    assert test_client.post("/testing/api/groups", json=empty).status_code == 422


def test_create_group_invalid_email_returns_422(client):
    test_client, _, _, _ = client

    bad_email = dict(GROUP_PAYLOAD, email="not-an-email")
    response = test_client.post("/testing/api/groups", json=bad_email)

    assert response.status_code == 422


def test_manual_execute_invalid_email_returns_422(client):
    test_client, _, _, _ = client

    bad_email = dict(MANUAL_PAYLOAD, email="not-an-email")
    response = test_client.post("/testing/api/runs", json=bad_email)

    assert response.status_code == 422


def test_group_start_runs_everything_and_finishes(client):
    test_client, service, fix, _ = client
    group = test_client.post("/testing/api/groups", json=GROUP_PAYLOAD).json()
    group_id = group["id"]

    start = test_client.post(f"/testing/api/groups/{group_id}/start")
    assert start.status_code == 200
    assert start.json()["status"] == "running"

    finished = wait_until_done(test_client, group_id)
    assert finished["completed_runs"] == 2
    assert finished["failed_runs"] == 0

    runs = test_client.get(f"/testing/api/groups/{group_id}/runs").json()["runs"]
    assert all(r["status"] == "done" for r in runs)
    assert [call.script for call in fix.calls] == ["script A", "script B"]

    detail = test_client.get(f"/testing/api/runs/{runs[0]['id']}").json()
    assert detail["verdict"] == "ok verdict"
    assert detail["email"] == "anna@example.com"

    again = test_client.post(f"/testing/api/groups/{group_id}/start")
    assert again.status_code == 409


def test_start_unknown_group_returns_404(client):
    test_client, _, _, _ = client

    response = test_client.post("/testing/api/groups/999/start")

    assert response.status_code == 404


def test_group_summary_generated_on_demand_and_cached(client):
    test_client, _, _, judge = client
    group = test_client.post("/testing/api/groups", json=GROUP_PAYLOAD).json()
    group_id = group["id"]

    before = test_client.post(f"/testing/api/groups/{group_id}/summary")
    assert before.status_code == 409

    test_client.post(f"/testing/api/groups/{group_id}/start")
    wait_until_done(test_client, group_id)

    summary = test_client.post(f"/testing/api/groups/{group_id}/summary")
    assert summary.status_code == 200
    assert summary.json()["summary"] == "common issues summary"
    assert len(judge.summary_batches) == 1

    again = test_client.post(f"/testing/api/groups/{group_id}/summary")
    assert again.json()["summary"] == "common issues summary"
    assert len(judge.summary_batches) == 1

    stored = test_client.get(f"/testing/api/groups/{group_id}").json()
    assert stored["summary"] == "common issues summary"


def test_second_group_rejected_while_first_runs(client):
    test_client, service, _, _ = client
    # Make the fixer slow so the first group holds the lock long enough.
    slow = SlowFixClient(delay=0.25)
    db = service._db
    slow_service = Service(db, slow, FakeJudge())
    app.dependency_overrides[get_testing_service] = lambda: slow_service

    group_a = test_client.post("/testing/api/groups", json=GROUP_PAYLOAD).json()
    group_b = test_client.post("/testing/api/groups", json=GROUP_PAYLOAD).json()

    assert test_client.post(f"/testing/api/groups/{group_a['id']}/start").status_code == 200

    busy_start = test_client.post(f"/testing/api/groups/{group_b['id']}/start")
    assert busy_start.status_code == 409

    manual = test_client.post("/testing/api/runs", json=MANUAL_PAYLOAD)
    assert manual.status_code == 409

    wait_until_done(test_client, group_a["id"])

    assert test_client.post(f"/testing/api/groups/{group_b['id']}/start").status_code == 200
    wait_until_done(test_client, group_b["id"])


class SlowFixClient(FakeFixClient):
    def __init__(self, delay: float, **kwargs) -> None:
        super().__init__(**kwargs)
        self.delay = delay

    async def fix(self, request):
        import asyncio

        await asyncio.sleep(self.delay)
        return await super().fix(request)
