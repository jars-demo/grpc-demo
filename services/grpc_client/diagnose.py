"""Turn a gRPC error into an explanation a learner can act on.

gRPC reports every failure as a status code plus a free-text detail. The code says which category
of problem it is; for connection problems the detail (from the TLS library) says what exactly went
wrong. This module explains both, without hiding the original error.
"""

from __future__ import annotations

from dataclasses import dataclass

import grpc

STATUS_EXPLANATIONS: dict[grpc.StatusCode, str] = {
    grpc.StatusCode.OK: "The call succeeded.",
    grpc.StatusCode.CANCELLED: "The call was cancelled, usually by the client.",
    grpc.StatusCode.INVALID_ARGUMENT: "The server rejected the request content. Fix the request; retrying will not help. (REST: 400/422)",
    grpc.StatusCode.DEADLINE_EXCEEDED: "The deadline passed before the server answered. The server may still have done the work. (REST: client timeout / 504)",
    grpc.StatusCode.NOT_FOUND: "The requested item does not exist. (REST: 404)",
    grpc.StatusCode.ALREADY_EXISTS: "The item already exists. (REST: 409)",
    grpc.StatusCode.PERMISSION_DENIED: "The caller is authenticated but not allowed to do this. Authentication is not authorization. (REST: 403)",
    grpc.StatusCode.RESOURCE_EXHAUSTED: "A limit was hit: message too large, too many concurrent calls, or a quota. (REST: 413/429)",
    grpc.StatusCode.FAILED_PRECONDITION: "The system is not in a state where this call can succeed.",
    grpc.StatusCode.ABORTED: "The call was aborted, typically by a concurrency conflict.",
    grpc.StatusCode.OUT_OF_RANGE: "A value was outside the valid range.",
    grpc.StatusCode.UNIMPLEMENTED: "The server does not implement this method. Client and server disagree about the contract (.proto). (REST: 404/501)",
    grpc.StatusCode.INTERNAL: "An internal error on the server or in the gRPC library. (REST: 500)",
    grpc.StatusCode.UNAVAILABLE: "No usable connection: the server is down, the port is wrong, or the TLS handshake failed. (REST: connection error / 503)",
    grpc.StatusCode.DATA_LOSS: "Unrecoverable data loss or corruption.",
    grpc.StatusCode.UNAUTHENTICATED: "The server could not verify who the caller is: no or invalid credentials. (REST: 401)",
    grpc.StatusCode.UNKNOWN: "An error without a more specific status, often an unhandled server exception.",
}

# Substrings of TLS / connection errors (BoringSSL and gRPC core) and what they mean. The first
# match wins, so specific causes come before generic ones.
DETAIL_HINTS: tuple[tuple[str, str], ...] = (
    (
        "certificate has expired",
        "The server certificate is outside its validity period. The fix is a new certificate on the "
        "server (certs.py rotate), never a client that ignores expiry.",
    ),
    (
        "CERTIFICATE_VERIFY_FAILED",
        "The client could not build a chain from the server certificate to a CA it trusts. --ca must "
        "be the CA that issued the server certificate (compare issuer and subject with certs.py inspect).",
    ),
    (
        "Hostname Verification Check failed",
        "Hostname mismatch: the host in --target is not in the server certificate's Subject "
        "Alternative Name list. Connect using a name the certificate lists (certs.py inspect server).",
    ),
    (
        "WRONG_VERSION_NUMBER",
        "The client spoke TLS to a port that does not speak TLS. Check the port, or whether this "
        "listener is the plaintext one.",
    ),
    (
        "Connection aborted",
        "The server closed the connection during the handshake. On the mutual TLS port this usually "
        "means the client sent no certificate or one the server does not trust. The server's log "
        "states the exact reason.",
    ),
    (
        "End of TCP stream",
        "The server closed the connection during the handshake. On the mutual TLS port this usually "
        "means the client sent no certificate or one the server does not trust; on a TLS port it can "
        "mean plaintext was sent to it. The server's log states the exact reason.",
    ),
    (
        "errors resolving",
        "The host name could not be resolved (DNS). Compose service names such as grpc-server only "
        "resolve inside the Compose network; from your machine, use localhost.",
    ),
    (
        "Connection refused",
        "Nothing is listening at that address and port. Is the server running? Is the port right?",
    ),
    (
        "Deadline Exceeded",
        "The deadline passed. Was the server slow, or is the deadline too tight for this call?",
    ),
)
GENERIC_HINT = "See the detail text: for connection failures it contains the TCP or TLS reason."


@dataclass(frozen=True)
class Diagnosis:
    code: str
    details: str
    meaning: str
    hints: tuple[str, ...]

    def render(self) -> str:
        lines = [
            f"RPC failed: {self.code}",
            f"  details: {self.details}",
            f"  meaning: {self.meaning}",
        ]
        lines += [f"  hint:    {hint}" for hint in self.hints]
        return "\n".join(lines)


def diagnose(error: grpc.RpcError) -> Diagnosis:
    code: grpc.StatusCode = error.code()
    details: str = error.details() or ""
    hint = next((h for needle, h in DETAIL_HINTS if needle.lower() in details.lower()), None)
    if hint is None and code == grpc.StatusCode.UNAVAILABLE:
        hint = GENERIC_HINT
    return Diagnosis(
        code=code.name,
        details=details,
        meaning=STATUS_EXPLANATIONS.get(code, "Unrecognized status."),
        hints=(hint,) if hint else (),
    )
