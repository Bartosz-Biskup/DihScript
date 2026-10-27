import re
from typing import Protocol

from pydantic import ValidationError

from repositories.models import PromptFixRequest, PromptFixRequestOutput

from .config import PROMPTS_DIR
from .exceptions import InvalidModelOutputException
from .llm_service import LLMServiceProtocol


class PromptFixerServiceProtocol(Protocol):
    async def fix(self, request: PromptFixRequest) -> PromptFixRequestOutput:
        ...


class PromptFixerService:
    def __init__(self, llm: LLMServiceProtocol) -> None:
        self._llm = llm

    async def fix(self, request: PromptFixRequest) -> PromptFixRequestOutput:
        raw = await self._llm.complete(
            self._build_prompt(request),
            response_format=self._response_format(),
        )
        return self._parse_output(raw)

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
    def _response_format() -> dict:
        return {
            "type": "json_schema",
            "json_schema": {
                "name": "prompt_fix_output",
                "schema": PromptFixRequestOutput.model_json_schema(),
            },
        }

    @staticmethod
    def _parse_output(raw: str) -> PromptFixRequestOutput:
        text = raw.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
        try:
            return PromptFixRequestOutput.model_validate_json(text)
        except ValidationError as e:
            raise InvalidModelOutputException("model returned invalid output") from e

    @staticmethod
    def _tag(name: str, content: str) -> str:
        return f"<{name}>\n{content}\n</{name}>"
