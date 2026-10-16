"""Certificate validation, hostname checks, mutual TLS and authorization, with real handshakes."""

from __future__ import annotations

import grpc
import pytest

from grpcdemo.v1 import workshop_pb2 as pb
from grpcdemo.v1 import workshop_pb2_grpc as pb_grpc
from tests.conftest import Servers


def hello(channel: grpc.Channel) -> pb.HelloReply:
    with channel:
        return pb_grpc.WorkshopServiceStub(channel).SayHello(pb.HelloRequest(name="t"), timeout=5)


def stats(channel: grpc.Channel) -> pb.ServerStats:
    with channel:
        return pb_grpc.AdminServiceStub(channel).GetServerStats(
            pb.GetServerStatsRequest(), timeout=5
        )


def failure(call: object) -> grpc.RpcError:
    with pytest.raises(grpc.RpcError) as info:
        call()  # type: ignore[operator]
    return info.value


# --- Server authentication (TLS) -------------------------------------------------------------


def test_tls_succeeds_with_workshop_ca_and_matching_hostname(servers: Servers) -> None:
    assert hello(servers.channel(servers.tls)).transport_security == "tls"


def test_tls_fails_when_client_trusts_only_public_roots(servers: Servers) -> None:
    error = failure(lambda: hello(servers.channel(servers.tls, ca=None)))

    assert error.code() == grpc.StatusCode.UNAVAILABLE
    assert "CERTIFICATE_VERIFY_FAILED" in error.details()


def test_tls_fails_when_client_trusts_a_different_ca(servers: Servers) -> None:
    error = failure(lambda: hello(servers.channel(servers.tls, ca="rogue-ca")))

    assert "CERTIFICATE_VERIFY_FAILED" in error.details()


def test_tls_fails_when_hostname_is_not_in_san(servers: Servers) -> None:
    # The server certificate lists DNS names only; 127.0.0.1 is not one of them.
    error = failure(lambda: hello(servers.channel(servers.tls, host="127.0.0.1")))

    assert error.code() == grpc.StatusCode.UNAVAILABLE
    assert "Hostname Verification Check failed" in error.details()


def test_tls_fails_for_expired_server_certificate(servers: Servers, expired_server: int) -> None:
    error = failure(lambda: hello(servers.channel(expired_server)))

    assert "certificate has expired" in error.details()


def test_tls_client_does_not_fall_back_to_plaintext(servers: Servers) -> None:
    # A TLS client pointed at the plaintext listener must fail, never silently downgrade.
    error = failure(lambda: hello(servers.channel(servers.plaintext)))

    assert error.code() == grpc.StatusCode.UNAVAILABLE


def test_plaintext_client_cannot_talk_to_tls_listener(servers: Servers) -> None:
    error = failure(lambda: hello(servers.channel(servers.tls, plaintext=True)))

    assert error.code() == grpc.StatusCode.UNAVAILABLE


# --- Client authentication (mutual TLS) ------------------------------------------------------


def test_mtls_succeeds_and_server_sees_verified_identity(servers: Servers) -> None:
    reply = hello(servers.channel(servers.mtls, client="client"))

    assert (reply.transport_security, reply.client_identity) == ("mtls", "workshop-client")


def test_mtls_rejects_client_without_certificate(servers: Servers) -> None:
    error = failure(lambda: hello(servers.channel(servers.mtls)))

    assert error.code() == grpc.StatusCode.UNAVAILABLE


def test_mtls_rejects_certificate_from_untrusted_ca_even_with_same_name(servers: Servers) -> None:
    # rogue-client.crt has CN=workshop-client, exactly like client.crt. The name is irrelevant:
    # the server only trusts certificates whose chain leads to the workshop CA.
    error = failure(lambda: hello(servers.channel(servers.mtls, client="rogue-client")))

    assert error.code() == grpc.StatusCode.UNAVAILABLE


# --- Authorization is separate from authentication -------------------------------------------


def test_admin_requires_a_client_certificate(servers: Servers) -> None:
    error = failure(lambda: stats(servers.channel(servers.tls)))

    assert error.code() == grpc.StatusCode.UNAUTHENTICATED


def test_admin_rejects_plaintext_callers(servers: Servers) -> None:
    error = failure(lambda: stats(servers.channel(servers.plaintext, plaintext=True)))

    assert error.code() == grpc.StatusCode.UNAUTHENTICATED


def test_trusted_certificate_alone_does_not_grant_admin_access(servers: Servers) -> None:
    error = failure(lambda: stats(servers.channel(servers.mtls, client="client")))

    assert error.code() == grpc.StatusCode.PERMISSION_DENIED
    assert "workshop-client" in error.details()


def test_admin_identity_is_authorized(servers: Servers) -> None:
    result = stats(servers.channel(servers.mtls, client="admin"))

    assert result.caller_identity == "workshop-admin"
    assert any(method.endswith("/SayHello") for method in result.calls_by_method)
