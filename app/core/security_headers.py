"""Security headers added to every response."""

from starlette.middleware.base import BaseHTTPMiddleware


# The API only returns JSON and file downloads. The interactive docs (dev only)
# load Swagger UI from a CDN, so they get a slightly wider policy.
API_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"

DOCS_CSP = (
    "default-src 'none'; "
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "img-src 'self' data: https://fastapi.tiangolo.com; "
    "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"
)

DOCS_PATHS = ("/docs", "/redoc", "/openapi.json")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request, call_next):

        response = await call_next(request)

        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Content-Security-Policy",
            DOCS_CSP if request.url.path.startswith(DOCS_PATHS) else API_CSP
        )

        return response
