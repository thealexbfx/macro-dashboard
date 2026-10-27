"""Small HTTP admission/body bounds; liveness/readiness are always reachable."""

import asyncio

from starlette.responses import JSONResponse


class RequestBounds:
    def __init__(self, app, max_inflight=8, max_body=65536, body_timeout=10):
        self.app = app
        self.max_inflight = max_inflight
        self.max_body = max_body
        self.inflight = 0
        self.body_timeout = body_timeout

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scope["path"].startswith("/api/v2/"):
            return await self.app(scope, receive, send)

        async def bounded_send(message):
            if message["type"] == "http.response.start":
                message = {
                    **message,
                    "headers": [
                        (k, v)
                        for k, v in message.get("headers", [])
                        if k.lower()
                        not in {b"cache-control", b"x-content-type-options"}
                    ]
                    + [
                        (b"cache-control", b"no-store"),
                        (b"x-content-type-options", b"nosniff"),
                    ],
                }
            await send(message)

        if self.inflight >= self.max_inflight:
            return await JSONResponse(
                {"detail": "Too many research requests; retry shortly."},
                status_code=429,
                headers={"Retry-After": "2"},
            )(scope, receive, bounded_send)
        self.inflight += 1
        try:
            if scope["method"] in {"POST", "PUT", "PATCH"}:
                length = dict(scope.get("headers", [])).get(b"content-length", b"0")
                try:
                    oversized = int(length) > self.max_body
                except ValueError:
                    oversized = True
                if oversized:
                    return await JSONResponse(
                        {"detail": "Research request exceeds 64 KiB."}, status_code=413
                    )(scope, receive, bounded_send)
                body = bytearray()
                deadline = asyncio.get_running_loop().time() + self.body_timeout
                while True:
                    try:
                        msg = await asyncio.wait_for(
                            receive(),
                            max(0, deadline - asyncio.get_running_loop().time()),
                        )
                    except TimeoutError:
                        return await JSONResponse(
                            {"detail": "Research request body timed out."},
                            status_code=408,
                        )(scope, receive, bounded_send)
                    if msg["type"] == "http.disconnect":
                        return
                    chunk = msg.get("body", b"")
                    if len(body) + len(chunk) > self.max_body:
                        return await JSONResponse(
                            {"detail": "Research request exceeds 64 KiB."},
                            status_code=413,
                        )(scope, receive, bounded_send)
                    body.extend(chunk)
                    if not msg.get("more_body", False):
                        break
                sent = False

                async def replay():
                    nonlocal sent
                    if not sent:
                        sent = True
                        return {
                            "type": "http.request",
                            "body": bytes(body),
                            "more_body": False,
                        }
                    return await receive()

                return await self.app(scope, replay, bounded_send)
            return await self.app(scope, receive, bounded_send)
        finally:
            self.inflight -= 1
