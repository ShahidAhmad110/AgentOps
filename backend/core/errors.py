import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


logger = logging.getLogger(__name__)


class APIError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 500) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code

    def to_dict(self) -> dict[str, Any]:
        return {"error": {"code": self.code, "message": self.message}}


def register_exception_handlers(application: FastAPI) -> None:
    @application.exception_handler(APIError)
    async def handle_api_error(request: Request, error: APIError) -> JSONResponse:
        logger.warning("API error handled", extra={"path": request.url.path, "error_code": error.code})
        return JSONResponse(status_code=error.status_code, content=error.to_dict())

    @application.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
        details = "; ".join(err.get("msg", "Invalid request") for err in error.errors())
        logger.warning("Validation error", extra={"path": request.url.path, "details": details})
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "VALIDATION_ERROR", "message": details or "Invalid request."}},
        )

    @application.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, error: StarletteHTTPException) -> JSONResponse:
        logger.warning("HTTP error", extra={"path": request.url.path, "status_code": error.status_code})
        return JSONResponse(
            status_code=error.status_code,
            content={"error": {"code": "HTTP_ERROR", "message": error.detail}},
        )

    @application.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, error: Exception) -> JSONResponse:
        logger.exception("Unhandled request error on %s: %s", request.url.path, error, extra={"path": request.url.path})
        error_msg = "An unexpected error occurred."
        if isinstance(error, (ConnectionRefusedError, OSError)) or "refused" in str(error).lower() or "connection" in str(error).lower():
            error_msg = "Database connection error. Please verify PostgreSQL is running and migrations have been applied."
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "INTERNAL_ERROR", "message": error_msg}},
        )