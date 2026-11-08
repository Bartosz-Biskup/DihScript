from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

from repositories.models import Change, PromptFixRequestInput, PromptFixRequestOutput
from services.fix_facade import FixRequest

Status = Literal["pending", "running", "done", "failed"]


class AutoRunItem(PromptFixRequestInput):
    """One input of an automatic group: everything except the email (group-level)."""


class GroupCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    items: list[AutoRunItem] = Field(min_length=1, max_length=1000)


class ManualExecuteRequest(FixRequest):
    """Full body of the real POST /fix endpoint."""


class GroupOut(BaseModel):
    id: int
    name: str
    email: str
    status: str
    created_at: datetime
    total_runs: int
    completed_runs: int
    failed_runs: int
    summary: str | None = None


class GroupListOut(BaseModel):
    groups: list[GroupOut]


class RunSummaryOut(BaseModel):
    id: int
    group_id: int | None
    mode: str
    length: int
    status: str
    has_fix_error: bool
    error: str | None = None
    created_at: datetime
    finished_at: datetime | None = None


class RunListOut(BaseModel):
    total: int
    runs: list[RunSummaryOut]


class RunDetailOut(BaseModel):
    id: int
    group_id: int | None
    email: str
    mode: str
    length: int
    script: str
    target_audience: str | None = None
    call_to_action: str | None = None
    status: str
    fixed_script: str | None = None
    fix_info: str | None = None
    fix_error: str | None = None
    changes: list[Change] = Field(default_factory=list)
    verdict: str | None = None
    error: str | None = None
    created_at: datetime
    finished_at: datetime | None = None


class ManualExecuteOut(BaseModel):
    input: ManualExecuteRequest
    output: PromptFixRequestOutput
    verdict: str | None = None


class SaveRunRequest(BaseModel):
    input: ManualExecuteRequest
    output: PromptFixRequestOutput
    verdict: str | None = None


class SaveRunOut(BaseModel):
    id: int


class GroupStartOut(BaseModel):
    status: str


class GroupSummaryOut(BaseModel):
    summary: str
