from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from .dependencies import get_job_manager, get_testing_service
from ..schemas import (
    ManualExecuteOut,
    ManualExecuteRequest,
    RunDetailOut,
    RunListOut,
    SaveRunOut,
    SaveRunRequest,
)
from ..services.exceptions import GroupNotFoundException
from ..services.job_manager import JobManager
from ..services.testing_service import TestingService

runs_router = APIRouter(tags=["runs"])


@runs_router.post("/runs", response_model=ManualExecuteOut)
async def execute_manual(
    payload: ManualExecuteRequest,
    testing_service: Annotated[TestingService, Depends(get_testing_service)],
    jobs: Annotated[JobManager, Depends(get_job_manager)],
) -> ManualExecuteOut:
    if jobs.is_busy():
        raise HTTPException(409, "An automatic run is in progress; wait for it to finish.")
    return await testing_service.execute(payload)


@runs_router.post("/runs/save", response_model=SaveRunOut, status_code=201)
def save_manual(
    payload: SaveRunRequest,
    testing_service: Annotated[TestingService, Depends(get_testing_service)],
) -> SaveRunOut:
    return SaveRunOut(id=testing_service.save_manual(payload))


@runs_router.get("/runs", response_model=RunListOut)
def list_manual_runs(
    testing_service: Annotated[TestingService, Depends(get_testing_service)],
    offset: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
) -> RunListOut:
    return testing_service.list_runs(None, offset, limit)


@runs_router.get("/runs/{run_id}", response_model=RunDetailOut)
def get_run(
    run_id: int,
    testing_service: Annotated[TestingService, Depends(get_testing_service)],
) -> RunDetailOut:
    try:
        return testing_service.get_run(run_id)
    except GroupNotFoundException as exc:
        raise HTTPException(404, str(exc)) from exc
