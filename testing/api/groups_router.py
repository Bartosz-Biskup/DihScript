from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from .dependencies import get_job_manager, get_testing_service
from ..schemas import (
    GroupCreateRequest,
    GroupListOut,
    GroupOut,
    GroupStartOut,
    GroupSummaryOut,
    RunListOut,
)
from ..services.exceptions import (
    GroupNotFinishedException,
    GroupNotFoundException,
)
from ..services.job_manager import JobManager
from ..services.testing_service import TestingService

groups_router = APIRouter(tags=["groups"])


@groups_router.post("/groups", response_model=GroupOut, status_code=201)
def create_group(
    payload: GroupCreateRequest,
    testing_service: Annotated[TestingService, Depends(get_testing_service)],
) -> GroupOut:
    group_id = testing_service.create_group(payload)
    return testing_service.get_group(group_id)


@groups_router.get("/groups", response_model=GroupListOut)
def list_groups(
    testing_service: Annotated[TestingService, Depends(get_testing_service)],
) -> GroupListOut:
    return GroupListOut(groups=testing_service.list_groups())


@groups_router.get("/groups/{group_id}", response_model=GroupOut)
def get_group(
    group_id: int,
    testing_service: Annotated[TestingService, Depends(get_testing_service)],
) -> GroupOut:
    try:
        return testing_service.get_group(group_id)
    except GroupNotFoundException as exc:
        raise HTTPException(404, str(exc)) from exc


@groups_router.post("/groups/{group_id}/start", response_model=GroupStartOut)
async def start_group(
    group_id: int,
    testing_service: Annotated[TestingService, Depends(get_testing_service)],
    jobs: Annotated[JobManager, Depends(get_job_manager)],
) -> GroupStartOut:
    try:
        group = testing_service.get_group(group_id)
    except GroupNotFoundException as exc:
        raise HTTPException(404, str(exc)) from exc

    if group.status == "done":
        raise HTTPException(409, "This group already finished.")
    if group.status == "running":
        raise HTTPException(409, "This group is already running.")
    if jobs.is_busy():
        raise HTTPException(409, "Another run is in progress; try again later.")

    testing_service.mark_group_status(group_id, "running")
    if not jobs.start(group_id, lambda: testing_service.run_group_job(group_id)):
        testing_service.mark_group_status(group_id, "pending")
        raise HTTPException(409, "Another run is in progress; try again later.")
    return GroupStartOut(status="running")


@groups_router.get("/groups/{group_id}/runs", response_model=RunListOut)
def list_group_runs(
    group_id: int,
    testing_service: Annotated[TestingService, Depends(get_testing_service)],
    offset: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
) -> RunListOut:
    return testing_service.list_runs(group_id, offset, limit)


@groups_router.post("/groups/{group_id}/summary", response_model=GroupSummaryOut)
async def generate_summary(
    group_id: int,
    testing_service: Annotated[TestingService, Depends(get_testing_service)],
) -> GroupSummaryOut:
    try:
        summary = await testing_service.generate_summary(group_id)
    except GroupNotFoundException as exc:
        raise HTTPException(404, str(exc)) from exc
    except GroupNotFinishedException as exc:
        raise HTTPException(409, str(exc)) from exc
    return GroupSummaryOut(summary=summary)
