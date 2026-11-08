from typing import Protocol

from repositories.models import PromptFixRequestInput, PromptFixRequestOutput
from services.llm_service import LLMService, LLMServiceProtocol

from ..config import JUDGE_MODEL, PROMPTS_DIR


class JudgeProtocol(Protocol):
    async def judge(self, request: PromptFixRequestInput, output: PromptFixRequestOutput) -> str:
        ...

    async def summarize_group(self, verdicts: list[str]) -> str:
        ...


class JudgeService:
    """Rates fixed scripts and summarizes groups using dedicated prompt files."""

    def __init__(self, llm: LLMServiceProtocol | None = None) -> None:
        self._llm = llm or LLMService(model=JUDGE_MODEL)

    async def judge(self, request: PromptFixRequestInput, output: PromptFixRequestOutput) -> str:
        prompt = (PROMPTS_DIR / "judge.txt").read_text(encoding="utf-8")
        user_content = "\n\n".join(
            [
                self._tag("context", self._context(request)),
                self._tag("original_script", request.script),
                self._tag("fixed_script", output.script),
                self._tag("fixer_info", output.info),
                self._tag("fixer_changes", self._changes_text(output)),
            ]
        )
        return await self._llm.complete(prompt.replace("{{USER_CONTENT}}", user_content))

    async def summarize_group(self, entries: list[str]) -> str:
        prompt = (PROMPTS_DIR / "group_summary.txt").read_text(encoding="utf-8")
        user_content = "\n\n".join(entries)
        return await self._llm.complete(prompt.replace("{{USER_CONTENT}}", user_content))

    @staticmethod
    def _context(request: PromptFixRequestInput) -> str:
        params = [f"<mode>{request.mode}</mode>", f"<length>{request.length}</length>"]
        if request.mode == "sell":
            params.append(f"<target_audience>{request.target_audience}</target_audience>")
            params.append(f"<call_to_action>{request.call_to_action}</call_to_action>")
        return "\n".join(params)

    @staticmethod
    def _changes_text(output: PromptFixRequestOutput) -> str:
        if not output.changes:
            return "(no changes reported)"
        return "\n".join(
            f"- [{c.start_char}:{c.end_char}] {c.reason}" for c in output.changes
        )

    @staticmethod
    def _tag(name: str, content: str) -> str:
        return f"<{name}>\n{content}\n</{name}>"
