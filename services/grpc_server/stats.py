"""Counts calls per method. A server interceptor sees every call before the servicer does."""

from __future__ import annotations

import logging
import threading
import time
from collections import Counter
from collections.abc import Callable
from typing import Any

import grpc

log = logging.getLogger("grpc_server.calls")


class CallStats:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._calls: Counter[str] = Counter()
        self._started = time.monotonic()

    def record(self, method: str) -> None:
        with self._lock:
            self._calls[method] += 1

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(self._calls)

    @property
    def uptime_seconds(self) -> float:
        return time.monotonic() - self._started


class StatsInterceptor(grpc.ServerInterceptor):  # type: ignore[type-arg]
    """Records the full method name of every incoming call and logs it (method only, no payload)."""

    def __init__(self, stats: CallStats) -> None:
        self._stats = stats

    def intercept_service(
        self,
        continuation: Callable[[grpc.HandlerCallDetails], grpc.RpcMethodHandler[Any, Any] | None],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> Any:
        method = handler_call_details.method
        self._stats.record(method)
        if not method.startswith(
            "/grpc.health.v1.Health/"
        ):  # container health checks: counted, not logged
            log.info("call %s", method)
        return continuation(handler_call_details)
