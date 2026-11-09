from typing import Annotated
from fastapi import APIRouter, Depends, Request

from repositories.models import PromptFixRequestOutput
from services.fix_facade import FixFacade, FixRequest
from .dependencies import get_fix_facade
from .rate_limiter import limiter

fix_router = APIRouter(prefix="/fix", tags=["fix"])


@fix_router.post("", response_model=PromptFixRequestOutput)
@limiter.limit("20/hour")
async def fix_script(
    request: Request,
    payload: FixRequest,
    fix_facade: Annotated[FixFacade, Depends(get_fix_facade)],
) -> PromptFixRequestOutput:
    return await fix_facade.fix(payload)
