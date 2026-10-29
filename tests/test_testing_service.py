import asyncio

import pytest

from testing.database import Database
from testing.schemas import GroupCreateRequest, ManualExecuteRequest, SaveRunRequest
from testing.services.exceptions import GroupNotFinishedException, GroupNotFoundException
from testing.services.testing_service import TestingService as Service
from testing.tables import TestRunTable as RunTable
from tests.testing_utils import FakeFixClient, FakeJudge, make_output


def make_service(tmp_path, fix_client=None, judge=None) -> Service:
    db = Database(f"sqlite:///{tmp_path}/testing.db")
    db.create_all()
    return Service(db, fix_client or FakeFixClient(), judge or FakeJudge())


def make_request(**overrides) -> ManualExecuteRequest:
    defaults = dict(
        email="anna@example.com",
        mode="watch",
        script="ORIGINAL SCRIPT",
        length=30,
        target_audience=None,
        call_to_action=None,
    )
    defaults.update(overrides)
    return ManualExecuteRequest(**defaults)


def make_group_payload(items: list[dict], name="batch-1", email="anna@example.com") -> GroupCreateRequest:
    return GroupCreateRequest(name=name, email=email, items=items)


def watch_item(script: str) -> dict:
    return {"mode": "watch", "script": script, "length": 30}


# --------------------------------------------------------------------- manual


def test_execute_runs_fix_and_judge(tmp_path):
    fix = FakeFixClient([make_output()])
    judge = FakeJudge("great hook")
    service = make_service(tmp_path, fix, judge)

    result = asyncio.run(service.execute(make_request()))

    assert result.output.script == "FIXED SCRIPT"
    assert result.verdict == "great hook"
    assert judge.judge_calls == 1
    assert len(fix.calls) == 1
    assert fix.calls[0].email == "anna@example.com"


def test_execute_skips_judge_when_fixer_returns_error(tmp_path):
    fix = FakeFixClient([make_output(script="", error="cannot fix this")])
    judge = FakeJudge()
    service = make_service(tmp_path, fix, judge)

    result = asyncio.run(service.execute(make_request()))

    assert result.output.error == "cannot fix this"
    assert result.verdict is None
    assert judge.judge_calls == 0


def test_save_manual_persists_run(tmp_path):
    fix = FakeFixClient()
    service = make_service(tmp_path, fix)
    output = asyncio.run(service.execute(make_request())).output

    run_id = service.save_manual(
        SaveRunRequest(input=make_request(), output=output, verdict="verdict text")
    )

    run = service.get_run(run_id)
    assert run.id == run_id
    assert run.group_id is None
    assert run.status == "done"
    assert run.script == "ORIGINAL SCRIPT"
    assert run.fixed_script == "FIXED SCRIPT"
    assert run.verdict == "verdict text"
    assert len(run.changes) == 1
    assert run.changes[0].reason == "slow warm-up cut"


def test_get_run_unknown_raises(tmp_path):
    service = make_service(tmp_path)
    with pytest.raises(GroupNotFoundException):
        service.get_run(999)


# --------------------------------------------------------------------- groups


def test_create_group_stores_pending_runs_in_order(tmp_path):
    service = make_service(tmp_path)
    group_id = service.create_group(
        make_group_payload([watch_item("A"), watch_item("B"), watch_item("C")])
    )

    group = service.get_group(group_id)
    assert group.status == "pending"
    assert group.total_runs == 3
    assert group.email == "anna@example.com"

    runs = service.list_runs(group_id, 0, 25).runs
    assert [run.status for run in runs] == ["pending", "pending", "pending"]
    details = [service.get_run(run.id).script for run in runs]
    assert details == ["A", "B", "C"]


def test_run_group_job_processes_runs_and_finishes_group(tmp_path):
    fix = FakeFixClient()
    judge = FakeJudge("ok")
    service = make_service(tmp_path, fix, judge)
    group_id = service.create_group(make_group_payload([watch_item("A"), watch_item("B")]))

    asyncio.run(service.run_group_job(group_id))

    group = service.get_group(group_id)
    assert group.status == "done"
    assert group.completed_runs == 2
    assert group.failed_runs == 0

    runs = service.list_runs(group_id, 0, 25).runs
    assert [run.status for run in runs] == ["done", "done"]
    assert service.get_run(runs[0].id).verdict == "ok"
    assert [call.script for call in fix.calls] == ["A", "B"]


def test_run_group_job_continues_after_failure(tmp_path):
    fix = FakeFixClient([RuntimeError("api down"), make_output()])
    service = make_service(tmp_path, fix)
    group_id = service.create_group(make_group_payload([watch_item("A"), watch_item("B")]))

    asyncio.run(service.run_group_job(group_id))

    group = service.get_group(group_id)
    assert group.status == "done"
    assert group.completed_runs == 1
    assert group.failed_runs == 1

    runs = service.list_runs(group_id, 0, 25).runs
    assert runs[0].status == "failed"
    assert "api down" in runs[0].error
    assert runs[1].status == "done"


def test_generate_summary_stores_and_returns_cached(tmp_path):
    judge = FakeJudge(summary="the hooks are all weak")
    service = make_service(tmp_path, judge=judge)
    group_id = service.create_group(make_group_payload([watch_item("A"), watch_item("B")]))
    asyncio.run(service.run_group_job(group_id))

    first = asyncio.run(service.generate_summary(group_id))
    second = asyncio.run(service.generate_summary(group_id))

    assert first == "the hooks are all weak"
    assert second == first
    assert len(judge.summary_batches) == 1
    assert service.get_group(group_id).summary == first


def test_generate_summary_raises_when_group_not_done(tmp_path):
    service = make_service(tmp_path)
    group_id = service.create_group(make_group_payload([watch_item("A")]))

    with pytest.raises(GroupNotFinishedException):
        asyncio.run(service.generate_summary(group_id))


def test_generate_summary_unknown_group_raises(tmp_path):
    service = make_service(tmp_path)
    with pytest.raises(GroupNotFoundException):
        asyncio.run(service.generate_summary(999))


def test_list_runs_paginates(tmp_path):
    service = make_service(tmp_path)
    group_id = service.create_group(make_group_payload([watch_item(f"S{i}") for i in range(3)]))

    page_one = service.list_runs(group_id, 0, 2)
    page_two = service.list_runs(group_id, 2, 2)

    assert page_one.total == 3
    assert len(page_one.runs) == 2
    assert len(page_two.runs) == 1
    assert [run.id for run in page_one.runs + page_two.runs] == sorted(
        run.id for run in page_one.runs + page_two.runs
    )


def test_list_manual_runs_only_returns_ungrouped(tmp_path):
    service = make_service(tmp_path)
    group_id = service.create_group(make_group_payload([watch_item("A")]))
    output = make_output()
    service.save_manual(SaveRunRequest(input=make_request(), output=output, verdict="v"))

    manual = service.list_runs(None, 0, 25)
    grouped = service.list_runs(group_id, 0, 25)

    assert manual.total == 1
    assert grouped.total == 1
    assert manual.runs[0].id != grouped.runs[0].id


def test_reset_running_returns_groups_to_pending(tmp_path):
    db = Database(f"sqlite:///{tmp_path}/testing.db")
    db.create_all()
    service = Service(db, FakeFixClient(), FakeJudge())
    group_id = service.create_group(make_group_payload([watch_item("A")]))
    service.mark_group_status(group_id, "running")
    with db.session_scope() as session:
        run = session.query(RunTable).filter(RunTable.group_id == group_id).first()
        run.status = "running"

    db.reset_running()

    assert service.get_group(group_id).status == "pending"
    assert service.list_runs(group_id, 0, 25).runs[0].status == "pending"
