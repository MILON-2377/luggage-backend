
import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors.base import AppError

logger = logging.getLogger(__name__)


HTTP_ERROR_CODES = {
    400: ("BAD_REQUEST", "The request is invalid."),
    401: ("UNAUTHORIZED", "Authentication is required."),
    403: ("FORBIDDEN", "You do not have permission to perform this action."),
    404: ("NOT_FOUND", "The requested resource was not found."),
    405: ("METHOD_NOT_ALLOWED", "The requested method is not allowed."),
    408: ("REQUEST_TIMEOUT", "The request timed out."),
    409: ("CONFLICT", "The request conflicts with the current resource state."),
    410: ("GONE", "The requested resource is no longer available."),
    413: ("PAYLOAD_TOO_LARGE", "The request payload is too large."),
    415: ("UNSUPPORTED_MEDIA_TYPE", "The request media type is not supported."),
    422: ("VALIDATION_ERROR", "The provided request data is invalid."),
    429: ("RATE_LIMIT_EXCEEDED", "Too many requests. Please try again later."),
    503: ("SERVICE_UNAVAILABLE", "The service is temporarily unavailable."),
}


def create_error_response(
    *,
    status_code: int,
    error_code: str,
    message: str,
    details: dict[str, Any] | list[Any] | None = None,
    headers: dict[str, str] | None = None,
    request_id: str | None = None,
) -> JSONResponse:
    content = {
        "success": False,
        "error": {
            "code": error_code,
            "message": message,
            "details": details,
        },
    }

    if request_id:
        content["request_id"] = request_id

    response_headers = dict(headers or {})

    if request_id:
        response_headers["X-Request-ID"] = request_id

    return JSONResponse(
        status_code=status_code,
        content=content,
        headers=response_headers,
    )


def get_request_id(request: Request) -> str | None:
    request_id = getattr(request.state, "request_id", None)

    if isinstance(request_id, str) and request_id:
        return request_id

    return None


async def app_error_handler(
    request: Request,
    exc: AppError,
) -> JSONResponse:
    return create_error_response(
        status_code=exc.status_code,
        error_code=exc.error_code,
        message=exc.message,
        details=exc.details,
        headers=getattr(exc, "headers", None),
        request_id=get_request_id(request),
    )


async def validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    errors = [
        {
            "field": ".".join(str(part) for part in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        }
        for error in exc.errors()
    ]

    return create_error_response(
        status_code=422,
        error_code="VALIDATION_ERROR",
        message="The provided request data is invalid.",
        details=errors,
        request_id=get_request_id(request),
    )


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    error_code, default_message = HTTP_ERROR_CODES.get(
        exc.status_code,
        ("HTTP_ERROR", "The request could not be processed."),
    )

    message = (
        exc.detail
        if isinstance(exc.detail, str) and exc.status_code < 500
        else default_message
    )

    return create_error_response(
        status_code=exc.status_code,
        error_code=error_code,
        message=message,
        headers=exc.headers,
        request_id=get_request_id(request),
    )


async def unexpected_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    logger.exception(
        "Unhandled application exception | method=%s | path=%s | request_id=%s",
        request.method,
        request.url.path,
        get_request_id(request),
    )

    return create_error_response(
        status_code=500,
        error_code="INTERNAL_ERROR",
        message="An unexpected internal error occurred.",
        request_id=get_request_id(request),
    )


def register_error_handlers(application: FastAPI) -> None:
    application.add_exception_handler(
        AppError,
        app_error_handler,
    )

    application.add_exception_handler(
        RequestValidationError,
        validation_error_handler,
    )

    application.add_exception_handler(
        StarletteHTTPException,
        http_exception_handler,
    )

    application.add_exception_handler(
        Exception,
        unexpected_error_handler,
    )
