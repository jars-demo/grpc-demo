"""End-to-end checks against the running Docker stack (python scripts/tasks.py up).

    uv run python scripts/smoke_test.py

Every check makes real requests to the published ports: REST over HTTP and HTTPS, all four gRPC
patterns over TLS, mutual TLS with authorization, and each failure the workshop teaches - which
must fail, and fail for the right reason. Exit code 0 only if every check passes.
"""

from __future__ import annotations

import ssl
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import grpc
import httpx

from common.tls import channel_credentials
from grpcdemo.v1 import workshop_pb2 as pb
from grpcdemo.v1 import workshop_pb2_grpc as pb_grpc

ROOT = Path(__file__).resolve().parent.parent
CERTS = ROOT / "certs" / "out"
CA = CERTS / "ca.crt"
TLS, MTLS, EXPIRED = "localhost:50051", "localhost:50052", "localhost:50053"
REST_HTTP, REST_HTTPS = "http://localhost:8080", "https://localhost:8443"
WEB = "http://localhost:3000"


def trust_workshop_ca() -> ssl.SSLContext:
    """Verifies the chain against the workshop CA and the hostname against the SAN."""
    return ssl.create_default_context(cafile=str(CA))


@dataclass(frozen=True)
class Check:
    name: str
    run: Callable[[], str]


def channel(target: str, ca: Path | None = CA, client: str | None = None) -> grpc.Channel:
    cert = CERTS / f"{client}.crt" if client else None
    key = CERTS / f"{client}.key" if client else None
    return grpc.secure_channel(target, channel_credentials(ca, cert, key))


def workshop(ch: grpc.Channel) -> pb_grpc.WorkshopServiceStub:
    return pb_grpc.WorkshopServiceStub(ch)


def expect_failure(fn: Callable[[], object], code: grpc.StatusCode, fragment: str = "") -> str:
    try:
        fn()
    except grpc.RpcError as exc:
        assert exc.code() == code, f"expected {code.name}, got {exc.code().name}: {exc.details()}"
        assert fragment in (exc.details() or ""), f"expected {fragment!r} in {exc.details()!r}"
        return f"{code.name}" + (f" ({fragment})" if fragment else "")
    raise AssertionError(f"expected {code.name}, but the call succeeded")


# --- REST ------------------------------------------------------------------------------------


def rest_http() -> str:
    r = httpx.post(f"{REST_HTTP}/v1/greetings", json={"name": "smoke"}, timeout=5)
    assert r.status_code == 200 and r.json()["transport_security"] == "http", r.text
    return f"{r.http_version} {r.status_code} {r.json()['message']}"


def rest_https() -> str:
    r = httpx.get(f"{REST_HTTPS}/v1/topics/grpc", verify=trust_workshop_ca(), timeout=5)
    assert r.status_code == 200 and r.json()["id"] == "grpc", r.text
    return f"{r.http_version} {r.status_code}, certificate verified"


def rest_https_404() -> str:
    r = httpx.get(f"{REST_HTTPS}/v1/topics/nope", verify=trust_workshop_ca(), timeout=5)
    assert r.status_code == 404 and r.json()["error"]["code"] == "NOT_FOUND", r.text
    return "404 NOT_FOUND"


def rest_https_hostname_mismatch() -> str:
    try:
        httpx.get("https://127.0.0.1:8443/health", verify=trust_workshop_ca(), timeout=5)
    except httpx.ConnectError as exc:
        assert "mismatch" in str(exc), exc
        return "rejected: IP address mismatch"
    raise AssertionError("connection to 127.0.0.1 should fail hostname verification")


# --- gRPC over TLS ---------------------------------------------------------------------------


def grpc_unary() -> str:
    with channel(TLS) as ch:
        reply = workshop(ch).SayHello(pb.HelloRequest(name="smoke"), timeout=5)
    assert reply.transport_security == "tls", reply
    return f"{reply.message} via {reply.transport_security}"


def grpc_server_streaming() -> str:
    with channel(TLS) as ch:
        events = list(
            workshop(ch).WatchEvents(pb.WatchEventsRequest(count=3, interval_ms=50), timeout=5)
        )
    assert [e.sequence for e in events] == [1, 2, 3]
    return f"{len(events)} events"


def grpc_client_streaming() -> str:
    samples = (pb.Measurement(label="smoke", value_ms=v) for v in (1.0, 2.0, 3.0))
    with channel(TLS) as ch:
        summary = workshop(ch).RecordMeasurements(samples, timeout=5)
    assert summary.count == 3 and summary.mean_ms == 2.0, summary
    return f"count={summary.count} mean={summary.mean_ms}"


def grpc_bidi_streaming() -> str:
    with channel(TLS) as ch:
        replies = list(
            workshop(ch).Chat(
                iter([pb.ChatMessage(text="a b"), pb.ChatMessage(text="c")]), timeout=5
            )
        )
    assert [r.word_count for r in replies] == [2, 1]
    return f"{len(replies)} replies"


def grpc_deadline() -> str:
    with channel(TLS) as ch:
        stub = workshop(ch)
        return expect_failure(
            lambda: stub.SayHello(pb.HelloRequest(name="x", simulated_delay_ms=1500), timeout=0.3),
            grpc.StatusCode.DEADLINE_EXCEEDED,
        )


def grpc_health() -> str:
    from grpc_health.v1 import health_pb2, health_pb2_grpc

    with channel(TLS) as ch:
        status = (
            health_pb2_grpc.HealthStub(ch).Check(health_pb2.HealthCheckRequest(), timeout=5).status
        )
    assert status == health_pb2.HealthCheckResponse.SERVING
    return "SERVING"


def grpc_unimplemented() -> str:
    with channel(TLS) as ch:
        call = ch.unary_unary(
            "/grpcdemo.v2.WorkshopService/SayHello",
            request_serializer=pb.HelloRequest.SerializeToString,
            response_deserializer=pb.HelloReply.FromString,
        )
        return expect_failure(
            lambda: call(pb.HelloRequest(name="x"), timeout=5), grpc.StatusCode.UNIMPLEMENTED
        )


# --- Expected TLS failures -------------------------------------------------------------------


def hello_on(ch_factory: Callable[[], grpc.Channel]) -> Callable[[], object]:
    def call() -> object:
        with ch_factory() as ch:
            return workshop(ch).SayHello(pb.HelloRequest(name="x"), timeout=5)

    return call


def tls_untrusted_ca() -> str:
    return expect_failure(
        hello_on(lambda: channel(TLS, ca=None)),
        grpc.StatusCode.UNAVAILABLE,
        "CERTIFICATE_VERIFY_FAILED",
    )


def tls_hostname_mismatch() -> str:
    return expect_failure(
        hello_on(lambda: channel("127.0.0.1:50051")),
        grpc.StatusCode.UNAVAILABLE,
        "Hostname Verification",
    )


def tls_expired() -> str:
    return expect_failure(
        hello_on(lambda: channel(EXPIRED)), grpc.StatusCode.UNAVAILABLE, "certificate has expired"
    )


# --- Mutual TLS and authorization ------------------------------------------------------------


def mtls_success() -> str:
    with channel(MTLS, client="client") as ch:
        reply = workshop(ch).SayHello(pb.HelloRequest(name="smoke"), timeout=5)
    assert (reply.transport_security, reply.client_identity) == ("mtls", "workshop-client"), reply
    return f"identity={reply.client_identity}"


def mtls_missing_cert() -> str:
    return expect_failure(hello_on(lambda: channel(MTLS)), grpc.StatusCode.UNAVAILABLE)


def mtls_untrusted_cert() -> str:
    return expect_failure(
        hello_on(lambda: channel(MTLS, client="rogue-client")), grpc.StatusCode.UNAVAILABLE
    )


def stats_as(client: str | None) -> Callable[[], object]:
    def call() -> object:
        with channel(MTLS if client else TLS, client=client) as ch:
            return pb_grpc.AdminServiceStub(ch).GetServerStats(
                pb.GetServerStatsRequest(), timeout=5
            )

    return call


def authz_denied() -> str:
    return expect_failure(stats_as("client"), grpc.StatusCode.PERMISSION_DENIED)


def authz_unauthenticated() -> str:
    return expect_failure(stats_as(None), grpc.StatusCode.UNAUTHENTICATED)


def authz_admin() -> str:
    stats = stats_as("admin")()
    assert stats.caller_identity == "workshop-admin", stats  # type: ignore[attr-defined]
    return f"caller={stats.caller_identity}"  # type: ignore[attr-defined]


def website() -> str:
    r = httpx.get(f"{WEB}/", timeout=5)
    assert r.status_code == 200 and "gRPC" in r.text, r.status_code
    w = httpx.get(f"{WEB}/workshop/05-first-grpc-call/", timeout=5)
    assert w.status_code == 200, w.status_code
    return "landing page and chapter served"


CHECKS = [
    Check("REST over HTTP", rest_http),
    Check("REST over HTTPS (verified)", rest_https),
    Check("REST 404 error body", rest_https_404),
    Check("HTTPS hostname mismatch fails", rest_https_hostname_mismatch),
    Check("gRPC health (TLS)", grpc_health),
    Check("gRPC unary (TLS)", grpc_unary),
    Check("gRPC server streaming", grpc_server_streaming),
    Check("gRPC client streaming", grpc_client_streaming),
    Check("gRPC bidirectional streaming", grpc_bidi_streaming),
    Check("gRPC deadline exceeded", grpc_deadline),
    Check("gRPC contract mismatch", grpc_unimplemented),
    Check("TLS untrusted CA fails", tls_untrusted_ca),
    Check("TLS hostname mismatch fails", tls_hostname_mismatch),
    Check("TLS expired certificate fails", tls_expired),
    Check("mTLS with client certificate", mtls_success),
    Check("mTLS without certificate fails", mtls_missing_cert),
    Check("mTLS untrusted certificate fails", mtls_untrusted_cert),
    Check("authz: trusted client denied", authz_denied),
    Check("authz: no client cert", authz_unauthenticated),
    Check("authz: admin allowed", authz_admin),
    Check("website", website),
]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    if not CA.exists():
        print(
            "certs/out/ca.crt not found: generate certificates and start the stack first.",
            file=sys.stderr,
        )
        return 2
    failed = 0
    started = time.monotonic()
    for check in CHECKS:
        try:
            detail = check.run()
            print(f"  PASS  {check.name:<34} {detail}")
        except Exception as exc:
            failed += 1
            print(f"  FAIL  {check.name:<34} {type(exc).__name__}: {exc}")
    print(
        f"\n{len(CHECKS) - failed}/{len(CHECKS)} checks passed in {time.monotonic() - started:.1f}s"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
