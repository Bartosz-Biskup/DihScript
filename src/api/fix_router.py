from typing import Annotated

from fastapi import APIRouter, Depends

from repositories.models import PromptFixRequestOutput
from services.fix_script_service import FixScriptRequest, FixScriptService

from .dependencies import get_fix_script_service

fix_router = APIRouter(prefix="/fix", tags=["fix"])


@fix_router.post("", response_model=PromptFixRequestOutput)
async def fix_script(
    payload: FixScriptRequest,
    fix_script_service: Annotated[FixScriptService, Depends(get_fix_script_service)],
) -> PromptFixRequestOutput:
    return await fix_script_service.fix_script(payload)
