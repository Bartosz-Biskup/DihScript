from typing import Annotated
from fastapi import APIRouter, Depends, Request
from repositories.models import FixRequest, PromptFixRequestOutput
from services.fix_facade import FixFacade
from .dependencies import get_fix_facade
from .rate_limiter import limiter, CONFIG

fix_router = APIRouter(prefix="/fix", tags=["fix"])


@fix_router.post("", response_model=PromptFixRequestOutput)
@limiter.limit(CONFIG.get("fix_router").get_limiter_config_in_slowapi_format())
async def fix_script(
    request: Request,
    payload: FixRequest,
    fix_facade: Annotated[FixFacade, Depends(get_fix_facade)],
) -> PromptFixRequestOutput:
    return await fix_facade.fix(payload)
