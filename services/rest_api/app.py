"""FastAPI application: the same capability as the gRPC unary RPCs, as a REST API.

    gRPC                                 REST
    SayHello(HelloRequest)               POST /v1/greetings          {"name": ..., "language": ...}
    ListTopics(ListTopicsRequest)        GET  /v1/topics?layer=...
    GetTopic(GetTopicRequest)            GET  /v1/topics/{topic_id}
    grpc.health.v1.Health/Check          GET  /health

Both call the same functions in `core`. The differences you see are the protocol's: URLs and
methods instead of RPC names, JSON instead of protobuf, HTTP status codes instead of gRPC status.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from core import greetings, topics
from core.errors import DomainError, InvalidArgument, NotFound
from rest_api.limits import BodySizeLimit

# (HTTP status, error code). The codes deliberately reuse the gRPC status names for comparison.
HTTP_STATUS_FOR: dict[type[DomainError], tuple[int, str]] = {
    InvalidArgument: (422, "INVALID_ARGUMENT"),
    NotFound: (404, "NOT_FOUND"),
}


class GreetingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")  # unknown fields are an error, not silently ignored
    name: str = Field(min_length=1, max_length=greetings.MAX_NAME_LENGTH, examples=["Ada"])
    language: str = Field(default="", max_length=8, examples=["en"])
    simulated_delay_ms: int = Field(default=0, ge=0, le=greetings.MAX_SIMULATED_DELAY_MS)


class GreetingResponse(BaseModel):
    message: str
    served_at: datetime
    transport_security: Literal["http", "https"]


class TopicModel(BaseModel):
    id: str
    title: str
    summary: str
    layer: topics.Layer
    minutes: int

    @classmethod
    def of(cls, topic: topics.Topic) -> TopicModel:
        return cls(
            id=topic.id,
            title=topic.title,
            summary=topic.summary,
            layer=topic.layer,
            minutes=topic.minutes,
        )


class TopicList(BaseModel):
    topics: list[TopicModel]


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorBody(BaseModel):
    error: ErrorDetail


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


def create_app(max_body_bytes: int = 16 * 1024) -> FastAPI:
    app = FastAPI(
        title="Workshop Service (REST)",
        version="1.0.0",
        description="The REST comparison for the gRPC & HTTPS workshop. Educational, not production.",
        responses={422: {"model": ErrorBody}},
    )
    app.add_middleware(BodySizeLimit, max_bytes=max_body_bytes)

    @app.middleware("http")
    async def security_headers(request: Request, call_next):  # type: ignore[no-untyped-def]
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(DomainError)
    async def domain_error(_: Request, exc: DomainError) -> JSONResponse:
        status, code = HTTP_STATUS_FOR.get(type(exc), (400, "FAILED_PRECONDITION"))
        return _error(status, code, str(exc))

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0]
        where = ".".join(str(p) for p in first["loc"] if p != "body")
        return _error(
            422, "INVALID_ARGUMENT", f"{where}: {first['msg']}" if where else first["msg"]
        )

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "SERVING"}

    @app.post("/v1/greetings", tags=["greetings"])
    async def create_greeting(body: GreetingRequest, request: Request) -> GreetingResponse:
        message = greetings.greet(body.name, body.language)
        if body.simulated_delay_ms:
            # If the client disconnects (its timeout), the server cancels this coroutine.
            await asyncio.sleep(body.simulated_delay_ms / 1000)
        scheme: Literal["http", "https"] = "https" if request.url.scheme == "https" else "http"
        return GreetingResponse(
            message=message, served_at=datetime.now(UTC), transport_security=scheme
        )

    @app.get("/v1/topics", tags=["topics"])
    async def list_topics(layer: Annotated[topics.Layer | None, Query()] = None) -> TopicList:
        return TopicList(topics=[TopicModel.of(t) for t in topics.list_topics(layer)])

    @app.get("/v1/topics/{topic_id}", tags=["topics"], responses={404: {"model": ErrorBody}})
    async def get_topic(topic_id: str) -> TopicModel:
        return TopicModel.of(topics.get_topic(topic_id))

    return app
