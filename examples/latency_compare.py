"""Measure, don't assume: sequential round-trip latency for REST (HTTPS) and gRPC (TLS).

    uv run python examples/latency_compare.py --calls 200

Both clients reuse one connection (HTTP keep-alive / one gRPC channel), send the equivalent unary
request, and verify certificates. The numbers describe THIS machine, THIS payload, sequential calls
over loopback. They say little about your production workload: change payload size, concurrency,
network distance or connection reuse and the picture can change. Run it several times.
"""

from __future__ import annotations

import argparse
import ssl
import statistics
import sys
import time
from collections.abc import Callable
from pathlib import Path

import grpc
import httpx

from common.tls import channel_credentials
from grpcdemo.v1 import workshop_pb2 as pb
from grpcdemo.v1 import workshop_pb2_grpc as pb_grpc


def measure(fn: Callable[[], object], calls: int, warmup: int) -> list[float]:
    for _ in range(warmup):  # connection setup and TLS handshake happen here, not in the samples
        fn()
    samples = []
    for _ in range(calls):
        start = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - start) * 1000)
    return samples


def report(name: str, samples: list[float]) -> None:
    ordered = sorted(samples)
    p = lambda q: ordered[min(len(ordered) - 1, int(q * len(ordered)))]  # noqa: E731
    print(
        f"{name:<22} n={len(samples):<5} p50={p(0.5):6.2f}ms  p95={p(0.95):6.2f}ms  "
        f"mean={statistics.fmean(samples):6.2f}ms  max={ordered[-1]:6.2f}ms"
    )


def grpc_call(target: str, ca: Path, fresh: bool) -> Callable[[], object]:
    creds = channel_credentials(ca)
    request = pb.HelloRequest(name="Ada")
    if fresh:  # a new channel per call: TCP connect + TLS handshake + HTTP/2 setup every time

        def call() -> object:
            with grpc.secure_channel(target, creds) as channel:
                return pb_grpc.WorkshopServiceStub(channel).SayHello(request, timeout=5)

        return call
    channel = grpc.secure_channel(target, creds)
    stub = pb_grpc.WorkshopServiceStub(channel)
    return lambda: stub.SayHello(request, timeout=5)


def rest_call(base_url: str, ca: Path, fresh: bool) -> Callable[[], object]:
    if fresh:  # a new client per call: TCP connect + TLS handshake every time

        def call() -> object:
            with httpx.Client(
                base_url=base_url, verify=ssl.create_default_context(cafile=str(ca)), timeout=5
            ) as client:
                return client.post("/v1/greetings", json={"name": "Ada"}).raise_for_status()

        return call
    client = httpx.Client(
        base_url=base_url, verify=ssl.create_default_context(cafile=str(ca)), timeout=5
    )
    return lambda: client.post("/v1/greetings", json={"name": "Ada"}).raise_for_status()


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare REST and gRPC round-trip latency")
    parser.add_argument("--calls", type=int, default=200)
    parser.add_argument("--warmup", type=int, default=20)
    parser.add_argument(
        "--fresh-connections",
        action="store_true",
        help="open a new connection for every call (pay the TLS handshake each time)",
    )
    parser.add_argument("--grpc-target", default="localhost:50051")
    parser.add_argument("--rest-url", default="https://localhost:8443")
    parser.add_argument("--ca", type=Path, default=Path("certs/out/ca.crt"))
    args = parser.parse_args()
    fresh = args.fresh_connections

    grpc_samples = measure(grpc_call(args.grpc_target, args.ca, fresh), args.calls, args.warmup)
    rest_samples = measure(rest_call(args.rest_url, args.ca, fresh), args.calls, args.warmup)

    mode = "a new connection per call" if fresh else "one reused connection"
    print(f"{args.calls} sequential calls each, after {args.warmup} warm-up calls, {mode}:\n")
    report("gRPC  SayHello (TLS)", grpc_samples)
    report("REST  POST (HTTPS)", rest_samples)
    print("\nThese are local loopback numbers for a tiny payload. Do not generalize them.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
