from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from repositories.exceptions import ModelValidationException
from services.exceptions import LLMException

from .api.dependencies import get_db
from .api.groups_router import groups_router
from .api.runs_router import runs_router
from .config import STATIC_DIR
from .services.fix_client import FixApiException


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = get_db()
    db.create_all()
    db.reset_running()
    yield


app = FastAPI(title="Script fixer testing tool", lifespan=lifespan)


@app.exception_handler(ModelValidationException)
async def model_validation_handler(request: Request, exc: ModelValidationException) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(FixApiException)
async def fix_api_error_handler(request: Request, exc: FixApiException) -> JSONResponse:
    """The main app's /fix call failed — surface its answer to the caller."""
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.exception_handler(LLMException)
async def llm_error_handler(request: Request, exc: LLMException) -> JSONResponse:
    """Judge/model failures are upstream problems, not internal bugs."""
    return JSONResponse(status_code=502, content={"detail": str(exc)})


# API routes must be registered before the static mount below, otherwise
# /testing/api/* would be swallowed by it.
app.include_router(runs_router, prefix="/testing/api")
app.include_router(groups_router, prefix="/testing/api")
app.mount("/testing", StaticFiles(directory=STATIC_DIR, html=True), name="testing-ui")


@app.get("/", include_in_schema=False)
def index() -> RedirectResponse:
    return RedirectResponse("/testing/")
