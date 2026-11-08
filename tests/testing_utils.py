from repositories.models import Change, PromptFixRequestOutput
from services.fix_facade import FixRequest


def make_output(
    script: str = "FIXED SCRIPT",
    info: str = "tightened the hook",
    error: str | None = None,
) -> PromptFixRequestOutput:
    return PromptFixRequestOutput(
        script=script,
        info=info,
        error=error,
        changes=[Change(start_char=0, end_char=7, reason="slow warm-up cut")],
    )


class FakeFixClient:
    """Returns queued responses (or a default output) and records every call."""

    def __init__(self, responses: list | None = None) -> None:
        self._responses = list(responses or [])
        self.calls: list[FixRequest] = []

    async def fix(self, request: FixRequest) -> PromptFixRequestOutput:
        self.calls.append(request)
        if self._responses:
            response = self._responses.pop(0)
            if isinstance(response, Exception):
                raise response
            return response
        return make_output()


class FakeJudge:
    def __init__(self, verdict: str = "solid fix", summary: str = "common issues summary") -> None:
        self.verdict = verdict
        self.summary = summary
        self.judge_calls = 0
        self.summary_batches: list[list[str]] = []

    async def judge(self, request, output) -> str:
        self.judge_calls += 1
        return self.verdict

    async def summarize_group(self, entries: list[str]) -> str:
        self.summary_batches.append(entries)
        return self.summary


class BusyJobManager:
    def is_busy(self) -> bool:
        return True

    def start(self, group_id, job) -> bool:
        return False
