"""X-Request-ID: taken from the proxy (Caddy) when well-formed, generated
otherwise; echoed on the response and attached to every log record."""

import re
import uuid

from app.core.logging_setup import request_id_var

_VALID = re.compile(r"^[A-Za-z0-9._-]{8,64}$")


class RequestIdMiddleware:
    """Pure ASGI (no BaseHTTPMiddleware): the context var stays set for the
    whole request, including sync endpoints run in the thread pool."""

    def __init__(self, app):

        self.app = app

    async def __call__(self, scope, receive, send):

        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        incoming = dict(scope["headers"]).get(b"x-request-id", b"").decode("latin-1")
        request_id = incoming if _VALID.match(incoming) else uuid.uuid4().hex
        token = request_id_var.set(request_id)

        async def send_with_id(message):
            if message["type"] == "http.response.start":
                headers = [(k, v) for k, v in message.get("headers", []) if k.lower() != b"x-request-id"]
                headers.append((b"x-request-id", request_id.encode()))
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        finally:
            request_id_var.reset(token)
