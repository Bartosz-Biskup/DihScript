from typing import Annotated

from fastapi import APIRouter, Depends

from repositories.models import PromptFixRequestOutput
from services.fix_facade import FixFacade, FixRequest

from .dependencies import get_fix_facade

fix_router = APIRouter(prefix="/fix", tags=["fix"])


@fix_router.post("", response_model=PromptFixRequestOutput)
async def fix_script(
    payload: FixRequest,
    fix_facade: Annotated[FixFacade, Depends(get_fix_facade)],
) -> PromptFixRequestOutput:
    return await fix_facade.fix(payload)
