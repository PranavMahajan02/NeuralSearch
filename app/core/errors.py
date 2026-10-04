"""Uniform error responses: every error body is {"detail": str, "code": str}."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException


logger = logging.getLogger("cogniseek.errors")


STATUS_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    413: "payload_too_large",
    415: "unsupported_media_type",
    422: "validation_error",
    429: "rate_limited",
    500: "internal_error",
    502: "bad_gateway",
    503: "service_unavailable"
}


class AppError(Exception):
    """Raise from services to return a specific status/code/message."""

    def __init__(self, status_code: int, detail: str, code: str = None):

        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail
        self.code = code or STATUS_CODES.get(status_code, "error")


def error_response(status_code: int, detail: str, code: str = None, headers=None):

    return JSONResponse(
        status_code=status_code,
        content={
            "detail": detail,
            "code": code or STATUS_CODES.get(status_code, "error")
        },
        headers=headers
    )


def _format_validation_error(exc: RequestValidationError) -> str:

    messages = []

    for err in exc.errors():
        loc = list(err.get("loc", ()))
        # Drop the leading location kind ("body", "query", ...), keep field names.
        if loc and loc[0] in ("body", "query", "path", "header", "cookie"):
            loc = loc[1:]
        location = ".".join(str(part) for part in loc)
        message = str(err.get("msg", "Invalid value.")).removeprefix("Value error, ")
        messages.append(f"{location}: {message}" if location else message)

    return "; ".join(messages) or "Invalid request."


async def app_error_handler(request: Request, exc: AppError):

    return error_response(exc.status_code, exc.detail, exc.code)


async def http_exception_handler(request: Request, exc: StarletteHTTPException):

    detail = exc.detail if isinstance(exc.detail, str) else STATUS_CODES.get(exc.status_code, "error")

    return error_response(
        exc.status_code,
        detail,
        headers=getattr(exc, "headers", None)
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):

    return error_response(422, _format_validation_error(exc))


async def rate_limit_handler(request: Request, exc: RateLimitExceeded):

    return error_response(
        429,
        "Too many requests. Please try again later.",
        headers={"Retry-After": "60"}
    )


async def unhandled_exception_handler(request: Request, exc: Exception):

    # Full traceback stays in the server log; the client gets no internals.
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)

    return error_response(500, "Internal server error.")


def register_error_handlers(app: FastAPI):

    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
