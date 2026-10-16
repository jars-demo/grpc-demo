"""Map domain errors to gRPC status codes, the way REST maps them to HTTP status codes."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import NoReturn

import grpc

from core.errors import DomainError, InvalidArgument, NotFound

STATUS_FOR: dict[type[DomainError], grpc.StatusCode] = {
    InvalidArgument: grpc.StatusCode.INVALID_ARGUMENT,
    NotFound: grpc.StatusCode.NOT_FOUND,
}


def abort(context: grpc.ServicerContext, error: DomainError) -> NoReturn:
    code = STATUS_FOR.get(type(error), grpc.StatusCode.FAILED_PRECONDITION)
    context.abort(code, str(error))
    raise AssertionError("context.abort always raises")  # pragma: no cover


@contextmanager
def domain_errors(context: grpc.ServicerContext) -> Iterator[None]:
    """Turn a DomainError raised inside the block into the matching gRPC status."""
    try:
        yield
    except DomainError as exc:
        abort(context, exc)
