"""Reject oversized request bodies before the application parses them (HTTP 413).

The body is read here, counting bytes, and only handed on if it fits. Reading stops at the first
chunk over the limit, so an oversized body never accumulates in memory. This also covers chunked
uploads, which have no Content-Length to check up front.

The gRPC server has the equivalent built in: `grpc.max_receive_message_length`, which fails the
call with RESOURCE_EXHAUSTED.
"""

from __future__ import annotations

import json

from starlette.types import ASGIApp, Message, Receive, Scope, Send


class BodySizeLimit:
    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        declared = dict(scope["headers"]).get(b"content-length")
        if declared is not None and declared.isdigit() and int(declared) > self.max_bytes:
            await self._reject(send)
            return

        messages: list[Message] = []
        received = 0
        while True:
            message = await receive()
            messages.append(message)
            if message["type"] != "http.request":
                break  # client disconnected
            received += len(message.get("body", b""))
            if received > self.max_bytes:
                await self._reject(send)
                return
            if not message.get("more_body", False):
                break

        replay = iter(messages)

        async def replay_receive() -> Message:
            # Hand the buffered body to the app, then defer to the real channel (disconnects).
            return next(replay, None) or await receive()

        await self.app(scope, replay_receive, send)

    async def _reject(self, send: Send) -> None:
        body = json.dumps(
            {
                "error": {
                    "code": "PAYLOAD_TOO_LARGE",
                    "message": f"request body exceeds {self.max_bytes} bytes",
                }
            }
        ).encode()
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
