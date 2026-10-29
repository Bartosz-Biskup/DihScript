from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from .api.dependencies import get_db
from .api.groups_router import groups_router
from .api.runs_router import runs_router
from .config import STATIC_DIR


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = get_db()
    db.create_all()
    db.reset_running()
    yield


app = FastAPI(title="Script fixer testing tool", lifespan=lifespan)

# API routes must be registered before the static mount below, otherwise
# /testing/api/* would be swallowed by it.
app.include_router(runs_router, prefix="/testing/api")
app.include_router(groups_router, prefix="/testing/api")
app.mount("/testing", StaticFiles(directory=STATIC_DIR, html=True), name="testing-ui")


@app.get("/", include_in_schema=False)
def index() -> RedirectResponse:
    return RedirectResponse("/testing/")
