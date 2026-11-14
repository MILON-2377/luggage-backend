import logging
import time

from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.perf_counter()

        method = scope.get("method", "")
        path = scope.get("path", "")
        status_code = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code

            if message["type"] == "http.response.start":
                status_code = message["status"]

            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)

        except Exception:
            duration = time.perf_counter() - start_time

            logger.exception(
                "HTTP request failed method=%s path=%s "
                "status_code=%s duration_ms=%.2f",
                method,
                path,
                status_code,
                duration * 1000,
            )
            raise

        else:
            duration = time.perf_counter() - start_time

            logger.info(
                "HTTP request completed method=%s path=%s "
                "status_code=%s duration_ms=%.2f",
                method,
                path,
                status_code,
                duration * 1000,
            )