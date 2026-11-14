
import re
from uuid import uuid4

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

REQUEST_ID_HEADER = "X-Request-ID"
REQUEST_ID_HEADER_BYTES = b"x-request-id"

REQUEST_ID_PATTERN = re.compile(r"^[a-zA-Z0-9._-]{1,128}$")


class RequestIDMiddleware:
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

        request_id = self._get_request_id(scope)

        scope.setdefault("state", {})["request_id"] = request_id

        async def send_with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers[REQUEST_ID_HEADER] = request_id

            await send(message)

        await self.app(scope, receive, send_with_request_id)

    @staticmethod
    def _get_request_id(scope: Scope) -> str:
        incoming_id = next(
            (
                value
                for name, value in scope.get("headers", [])
                if name == REQUEST_ID_HEADER_BYTES
            ),
            b"",
        )

        try:
            decoded_id = incoming_id.decode("ascii")
        except UnicodeDecodeError:
            decoded_id = ""

        if REQUEST_ID_PATTERN.fullmatch(decoded_id):
            return decoded_id

        return str(uuid4())
