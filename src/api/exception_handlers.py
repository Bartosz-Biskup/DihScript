from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from repositories.exceptions import (
    AlreadyExistsException as RepoAlreadyExists,
    ModelValidationException,
    NotFoundException as RepoNotFound,
    RepositoryException,
)
from services.exceptions import (
    AlreadyExistsException as ServiceAlreadyExists,
    EmptyPromptException,
    InvalidModelResponseException,
    LLMException,
    ModelProviderException,
    NotFoundException as ServiceNotFound,
    ServiceException,
)


def _handler(status_code: int, default_detail: str):
    def handle(request: Request, exc: Exception) -> JSONResponse:
        if status_code == 500:
            return JSONResponse(status_code=status_code, content={"detail": default_detail})

        return JSONResponse(status_code=status_code, content={"detail": str(exc) or default_detail})

    return handle


MAPPING: dict[type[Exception] | tuple[type[Exception], ...], tuple[int, str]] = {
    (RepoNotFound, ServiceNotFound): (404, "Not found"),
    (RepoAlreadyExists, ServiceAlreadyExists): (409, "Already exists"),
    ModelValidationException: (422, "Validation error"),
    ValidationError: (422, "Validation error"),
    EmptyPromptException: (400, "Bad request"),
    (InvalidModelResponseException, ModelProviderException, LLMException): (502, "Model provider error"),
    ValueError: (400, "Bad request"),
}


def register_exception_handlers(app: FastAPI) -> None:
    for exc_types, (status, default) in MAPPING.items():
        handler = _handler(status, default)
        if isinstance(exc_types, tuple):
            for exc_type in exc_types:
                app.add_exception_handler(exc_type, handler)
        else:
            app.add_exception_handler(exc_types, handler)

    app.add_exception_handler(RepositoryException, _handler(500, "Repository error"))
    app.add_exception_handler(ServiceException, _handler(500, "Service error"))
    app.add_exception_handler(Exception, _handler(500, "Internal server error"))
