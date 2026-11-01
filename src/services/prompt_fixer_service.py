from typing import Protocol

from repositories.models import PromptFixRequest, PromptFixRequestOutput

from .config import PROMPTS_DIR
from .llm_service import LLMServiceProtocol


class PromptFixerServiceProtocol(Protocol):
    async def fix(self, request: PromptFixRequest) -> PromptFixRequestOutput:
        ...


class PromptFixerService:
    def __init__(self, llm: LLMServiceProtocol) -> None:
        self._llm = llm

    async def fix(self, request: PromptFixRequest) -> PromptFixRequestOutput:
        return await self._llm.complete(
            self._build_prompt(request),
            response_format=PromptFixRequestOutput,
        )

    def _build_prompt(self, request: PromptFixRequest) -> str:
        template = (PROMPTS_DIR / "script_fixer.txt").read_text(encoding="utf-8")

        params = [f"<mode>{request.mode}</mode>", f"<length>{request.length}</length>"]
        if request.mode == "sell":
            params.append(f"<target_audience>{request.target_audience}</target_audience>")
            params.append(f"<call_to_action>{request.call_to_action}</call_to_action>")

        user_content = "\n\n".join(
            [
                self._tag("context", "\n".join(params)),
                self._tag("user_script", request.script),
            ]
        )

        return template.replace("{{USER_CONTENT}}", user_content)

    @staticmethod
    def _tag(name: str, content: str) -> str:
        return f"<{name}>\n{content}\n</{name}>"
