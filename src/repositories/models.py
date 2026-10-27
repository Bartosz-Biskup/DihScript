from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .exceptions import ModelValidationException

Length = Literal[30, 60, 90]


class PromptFixRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    mode: Literal["watch", "sell"] = "watch"
    script: str = Field(min_length=1)
    length: Length = 30
    target_audience: str | None = None
    call_to_action: str | None = None

    @model_validator(mode="after")
    def _check_mode_fields(self):
        if self.mode == "sell":
            missing = [
                name
                for name in ("target_audience", "call_to_action")
                if not getattr(self, name)
            ]
            if missing:
                raise ModelValidationException(f"required in sell mode: {', '.join(missing)}")
        else:
            self.target_audience = None
            self.call_to_action = None
        return self


class Change(BaseModel):
    start_char: int = Field(ge=0)
    end_char: int = Field(ge=0)
    reason: str

    @model_validator(mode="after")
    def _check_bounds(self):
        if self.end_char < self.start_char:
            raise ModelValidationException("end_char must be greater than or equal to start_char")
        return self


class PromptFixRequestOutput(BaseModel):
    script: str
    info: str
    error: str | None = None
    changes: list[Change] = Field(default_factory=list)


class Subscriber(BaseModel):
    name: str
    email: str
    run_count: int = 0
