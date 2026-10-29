import json
from datetime import datetime

from sqlalchemy import func

from repositories.models import PromptFixRequestOutput
from services.fix_script_service import FixScriptRequest

from ..database import Database
from ..schemas import (
    GroupCreateRequest,
    GroupOut,
    ManualExecuteOut,
    ManualExecuteRequest,
    RunDetailOut,
    RunListOut,
    RunSummaryOut,
    SaveRunRequest,
)
from ..tables import GroupTable, TestRunTable
from .exceptions import GroupNotFoundException, GroupNotFinishedException
from .fix_client import FixApiClientProtocol
from .judge import JudgeProtocol

_SUMMARY_SCRIPT_LIMIT = 600
_SUMMARY_VERDICT_LIMIT = 400


class TestingService:
    def __init__(
        self,
        db: Database,
        fix_client: FixApiClientProtocol,
        judge: JudgeProtocol,
    ) -> None:
        self._db = db
        self._fix = fix_client
        self._judge = judge

    # ---------------------------------------------------------------- manual

    async def execute(self, request: ManualExecuteRequest) -> ManualExecuteOut:
        output = await self._fix.fix(request)
        verdict = None if output.error is not None else await self._judge.judge(request, output)
        return ManualExecuteOut(input=request, output=output, verdict=verdict)

    def save_manual(self, payload: SaveRunRequest) -> int:
        inp = payload.input
        with self._db.session_scope() as session:
            row = self._row_from(
                group_id=None,
                email=inp.email,
                mode=inp.mode,
                length=inp.length,
                script=inp.script,
                target_audience=inp.target_audience,
                call_to_action=inp.call_to_action,
                status="done",
                output=payload.output,
                verdict=payload.verdict,
            )
            session.add(row)
            session.flush()
            return row.id

    # ---------------------------------------------------------------- groups

    def create_group(self, payload: GroupCreateRequest) -> int:
        with self._db.session_scope() as session:
            group = GroupTable(name=payload.name, email=payload.email, status="pending")
            session.add(group)
            session.flush()
            for item in payload.items:
                session.add(
                    TestRunTable(
                        group_id=group.id,
                        email=payload.email,
                        mode=item.mode,
                        length=item.length,
                        script=item.script,
                        target_audience=item.target_audience,
                        call_to_action=item.call_to_action,
                        status="pending",
                    )
                )
            return group.id

    def list_groups(self) -> list[GroupOut]:
        with self._db.session_scope() as session:
            groups = session.query(GroupTable).order_by(GroupTable.id.desc()).all()
            counts = self._status_counts(session, None)
            return [self._group_out(g, counts.get(g.id, {})) for g in groups]

    def get_group(self, group_id: int) -> GroupOut:
        with self._db.session_scope() as session:
            group = session.get(GroupTable, group_id)
            if group is None:
                raise GroupNotFoundException(f"Group with id={group_id} not found")
            counts = self._status_counts(session, group_id)
            return self._group_out(group, counts.get(group_id, {}))

    def mark_group_status(self, group_id: int, status: str) -> None:
        with self._db.session_scope() as session:
            group = session.get(GroupTable, group_id)
            if group is not None:
                group.status = status

    async def run_group_job(self, group_id: int) -> None:
        with self._db.session_scope() as session:
            group = session.get(GroupTable, group_id)
            if group is None:
                return
            group.status = "running"
            email = group.email
            run_ids = [
                row_id
                for (row_id,) in session.query(TestRunTable.id)
                .filter(TestRunTable.group_id == group_id)
                .order_by(TestRunTable.id)
            ]

        try:
            for run_id in run_ids:
                await self.run_one(run_id, email)
        finally:
            with self._db.session_scope() as session:
                group = session.get(GroupTable, group_id)
                if group is not None:
                    group.status = "done"

    async def run_one(self, run_id: int, email: str) -> None:
        with self._db.session_scope() as session:
            row = session.get(TestRunTable, run_id)
            if row is None:
                return
            row.status = "running"
            request = self._request_from_row(row, email)

        try:
            output = await self._fix.fix(request)
            verdict = None if output.error is not None else await self._judge.judge(request, output)
            self._finish_run(run_id, status="done", output=output, verdict=verdict)
        except Exception as exc:  # keep the group going even if one test blows up
            self._finish_run(run_id, status="failed", error=str(exc))

    async def generate_summary(self, group_id: int) -> str:
        with self._db.session_scope() as session:
            group = session.get(GroupTable, group_id)
            if group is None:
                raise GroupNotFoundException(f"Group with id={group_id} not found")
            if group.status != "done":
                raise GroupNotFinishedException("Group is not finished yet")
            if group.summary:
                return group.summary
            rows = (
                session.query(TestRunTable)
                .filter(TestRunTable.group_id == group_id)
                .order_by(TestRunTable.id)
                .all()
            )
            entries = [self._summary_entry(row, index) for index, row in enumerate(rows)]

        summary = await self._judge.summarize_group(entries)

        with self._db.session_scope() as session:
            group = session.get(GroupTable, group_id)
            group.summary = summary
        return summary

    # --------------------------------------------------------------- browsing

    def list_runs(self, group_id: int | None, offset: int, limit: int) -> RunListOut:
        with self._db.session_scope() as session:
            condition = (
                TestRunTable.group_id.is_(None)
                if group_id is None
                else TestRunTable.group_id == group_id
            )
            query = session.query(TestRunTable).filter(condition)
            total = query.count()
            rows = query.order_by(TestRunTable.id).offset(offset).limit(limit).all()
            return RunListOut(total=total, runs=[self._run_summary(row) for row in rows])

    def get_run(self, run_id: int) -> RunDetailOut:
        with self._db.session_scope() as session:
            row = session.get(TestRunTable, run_id)
            if row is None:
                raise GroupNotFoundException(f"Run with id={run_id} not found")
            return self._run_detail(row)

    # ---------------------------------------------------------------- helpers

    @staticmethod
    def _row_from(
        *,
        group_id: int | None,
        email: str,
        mode: str,
        length: int,
        script: str,
        target_audience: str | None,
        call_to_action: str | None,
        status: str,
        output: PromptFixRequestOutput,
        verdict: str | None,
    ) -> TestRunTable:
        return TestRunTable(
            group_id=group_id,
            email=email,
            mode=mode,
            length=length,
            script=script,
            target_audience=target_audience,
            call_to_action=call_to_action,
            status=status,
            fixed_script=output.script,
            fix_info=output.info,
            fix_error=output.error,
            changes_json=json.dumps([change.model_dump() for change in output.changes]),
            verdict=verdict,
            finished_at=datetime.now(),
        )

    @staticmethod
    def _request_from_row(row: TestRunTable, email: str) -> FixScriptRequest:
        return FixScriptRequest(
            email=email,
            mode=row.mode,
            script=row.script,
            length=row.length,
            target_audience=row.target_audience,
            call_to_action=row.call_to_action,
        )

    def _finish_run(
        self,
        run_id: int,
        *,
        status: str,
        output: PromptFixRequestOutput | None = None,
        verdict: str | None = None,
        error: str | None = None,
    ) -> None:
        with self._db.session_scope() as session:
            row = session.get(TestRunTable, run_id)
            if row is None:
                return
            row.status = status
            row.error = error
            row.finished_at = datetime.now()
            if output is not None:
                row.fixed_script = output.script
                row.fix_info = output.info
                row.fix_error = output.error
                row.changes_json = json.dumps([c.model_dump() for c in output.changes])
                row.verdict = verdict

    @staticmethod
    def _status_counts(session, group_id: int | None) -> dict[int | None, dict[str, int]]:
        query = session.query(
            TestRunTable.group_id, TestRunTable.status, func.count(TestRunTable.id)
        )
        if group_id is not None:
            query = query.filter(TestRunTable.group_id == group_id)
        query = query.group_by(TestRunTable.group_id, TestRunTable.status)
        result: dict[int | None, dict[str, int]] = {}
        for gid, status, count in query.all():
            result.setdefault(gid, {})[status] = count
        return result

    @staticmethod
    def _group_out(group: GroupTable, counts: dict[str, int]) -> GroupOut:
        return GroupOut(
            id=group.id,
            name=group.name,
            email=group.email,
            status=group.status,
            created_at=group.created_at,
            total_runs=sum(counts.values()),
            completed_runs=counts.get("done", 0),
            failed_runs=counts.get("failed", 0),
            summary=group.summary,
        )

    @staticmethod
    def _run_summary(row: TestRunTable) -> RunSummaryOut:
        return RunSummaryOut(
            id=row.id,
            group_id=row.group_id,
            mode=row.mode,
            length=row.length,
            status=row.status,
            has_fix_error=bool(row.fix_error),
            error=row.error,
            created_at=row.created_at,
            finished_at=row.finished_at,
        )

    @staticmethod
    def _run_detail(row: TestRunTable) -> RunDetailOut:
        return RunDetailOut(
            id=row.id,
            group_id=row.group_id,
            email=row.email,
            mode=row.mode,
            length=row.length,
            script=row.script,
            target_audience=row.target_audience,
            call_to_action=row.call_to_action,
            status=row.status,
            fixed_script=row.fixed_script,
            fix_info=row.fix_info,
            fix_error=row.fix_error,
            changes=json.loads(row.changes_json) if row.changes_json else [],
            verdict=row.verdict,
            error=row.error,
            created_at=row.created_at,
            finished_at=row.finished_at,
        )

    @classmethod
    def _summary_entry(cls, row: TestRunTable, index: int) -> str:
        parts = [f"--- test {index + 1} (status={row.status}) ---"]
        parts.append(
            f"context: mode={row.mode}, length={row.length}, "
            f"audience={row.target_audience}, cta={row.call_to_action}"
        )
        parts.append("original script:\n" + cls._truncate(row.script, _SUMMARY_SCRIPT_LIMIT))
        if row.fixed_script:
            parts.append("fixed script:\n" + cls._truncate(row.fixed_script, _SUMMARY_SCRIPT_LIMIT))
        if row.fix_error:
            parts.append("fixer error: " + row.fix_error)
        if row.error:
            parts.append("pipeline error: " + row.error)
        parts.append(
            "judge verdict:\n"
            + (cls._truncate(row.verdict, _SUMMARY_VERDICT_LIMIT) if row.verdict else "(none)")
        )
        return "\n".join(parts)

    @staticmethod
    def _truncate(text: str, limit: int) -> str:
        return text if len(text) <= limit else text[:limit] + "…"
